"""Ticket workflow: creation, queue queries, admin updates, replies and notes.

Routes stay thin and call these functions. Access rules live here too: an author
can only reach their own tickets, and admin-only operations check the role.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import Select, case, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ConflictError, ForbiddenError, NotFoundError, ValidationFailedError
from app.models import Book, InternalNote, Ticket, TicketMessage, User
from app.models.enums import AIStatus, FieldSource, TicketPriority, TicketStatus, UserRole
from app.models.types import utcnow
from app.schemas.ticket import MessageCreate, TicketCreate, TicketStats, TicketUpdate
from app.services.events import EventType, TicketEvent, broker

UNRESOLVED = (TicketStatus.OPEN, TicketStatus.IN_PROGRESS)

# Urgency ordering for the queue. Untriaged tickets sit between high and medium so a
# brand-new ticket is visible straight away, even before (or without) AI triage.
_PRIORITY_RANK = case(
    (Ticket.priority == TicketPriority.CRITICAL, 0),
    (Ticket.priority == TicketPriority.HIGH, 1),
    (Ticket.priority.is_(None), 2),
    (Ticket.priority == TicketPriority.MEDIUM, 3),
    else_=4,
)
_STATUS_RANK = case(
    (Ticket.status.in_(UNRESOLVED), 0),
    (Ticket.status == TicketStatus.RESOLVED, 1),
    else_=2,
)

SORTS = {
    # Unresolved first, then most urgent, then oldest: the order an ops team works in.
    "urgency": (_STATUS_RANK, _PRIORITY_RANK, Ticket.created_at.asc()),
    "newest": (Ticket.created_at.desc(),),
    "oldest": (Ticket.created_at.asc(),),
    "updated": (Ticket.updated_at.desc(),),
}


@dataclass
class TicketFilters:
    status: list[TicketStatus] | None = None
    category: list[str] | None = None
    priority: list[str] | None = None
    assigned: str | None = None  # "me" | "unassigned"
    awaiting_reply: bool | None = None
    book_id: str | None = None
    created_from: date | None = None
    created_to: date | None = None
    search: str | None = None
    sort: str = "urgency"


def _with_relations(query: Select) -> Select:
    return query.options(
        selectinload(Ticket.messages).selectinload(TicketMessage.sender),
        selectinload(Ticket.book),
        selectinload(Ticket.author),
        selectinload(Ticket.assigned_admin),
    )


# --- Reads ------------------------------------------------------------------------------


def list_tickets(
    db: Session, user: User, filters: TicketFilters, page: int, page_size: int
) -> tuple[list[Ticket], int]:
    query = select(Ticket)
    if user.role == UserRole.AUTHOR:
        query = query.where(Ticket.author_id == user.author_id)

    if filters.status:
        query = query.where(Ticket.status.in_(filters.status))
    if filters.category:
        query = query.where(Ticket.category.in_(filters.category))
    if filters.priority:
        query = query.where(Ticket.priority.in_(filters.priority))
    if filters.assigned == "me":
        query = query.where(Ticket.assigned_admin_id == user.id)
    elif filters.assigned == "unassigned":
        query = query.where(Ticket.assigned_admin_id.is_(None))
    if filters.awaiting_reply is not None:
        query = query.where(Ticket.awaiting_team_reply == filters.awaiting_reply)
    if filters.book_id:
        query = query.where(Ticket.book_id == filters.book_id)
    if filters.created_from:
        query = query.where(Ticket.created_at >= _start_of_day(filters.created_from))
    if filters.created_to:
        query = query.where(Ticket.created_at < _start_of_day(filters.created_to + timedelta(days=1)))
    if filters.search:
        pattern = f"%{filters.search.strip()}%"
        query = query.where(or_(Ticket.subject.ilike(pattern), Ticket.description.ilike(pattern)))

    total = db.scalar(select(func.count()).select_from(query.subquery()))
    query = query.order_by(*SORTS[filters.sort], Ticket.id).offset((page - 1) * page_size).limit(page_size)
    return list(db.scalars(_with_relations(query)).all()), total


def get_ticket(db: Session, user: User, ticket_id: int) -> Ticket:
    # populate_existing: after an update in this session, reload relationships
    # (e.g. assigned_admin) instead of returning the stale cached ones.
    query = _with_relations(select(Ticket).where(Ticket.id == ticket_id)).execution_options(populate_existing=True)
    if user.role == UserRole.ADMIN:
        query = query.options(selectinload(Ticket.internal_notes).selectinload(InternalNote.admin))
    ticket = db.scalar(query)
    # Another author's ticket is "not found", so ticket IDs can't be probed.
    if ticket is None or (user.role == UserRole.AUTHOR and ticket.author_id != user.author_id):
        raise NotFoundError("Ticket not found")
    return ticket


def ticket_stats(db: Session) -> TicketStats:
    def count(*conditions) -> int:
        return db.scalar(select(func.count(Ticket.id)).where(*conditions)) or 0

    unresolved = Ticket.status.in_(UNRESOLVED)
    return TicketStats(
        open=count(Ticket.status == TicketStatus.OPEN),
        in_progress=count(Ticket.status == TicketStatus.IN_PROGRESS),
        resolved=count(Ticket.status == TicketStatus.RESOLVED),
        closed=count(Ticket.status == TicketStatus.CLOSED),
        unassigned=count(unresolved, Ticket.assigned_admin_id.is_(None)),
        awaiting_reply=count(unresolved, Ticket.awaiting_team_reply.is_(True)),
        critical_open=count(unresolved, Ticket.priority == TicketPriority.CRITICAL),
        pending_triage=count(Ticket.ai_status == AIStatus.PENDING),
    )


# --- Writes -----------------------------------------------------------------------------


def create_ticket(db: Session, user: User, data: TicketCreate) -> Ticket:
    if user.role != UserRole.AUTHOR:
        raise ForbiddenError("Only authors can raise tickets")
    if data.book_id is not None:
        book = db.get(Book, data.book_id)
        if book is None or book.author_id != user.author_id:
            raise ValidationFailedError(
                "Please choose one of your own books", [{"field": "book_id", "message": "Unknown book"}]
            )

    ticket = Ticket(author_id=user.author_id, **data.model_dump())
    db.add(ticket)
    db.commit()
    broker.publish(TicketEvent(EventType.TICKET_CREATED, ticket.id, ticket.author_id))
    return get_ticket(db, user, ticket.id)


def update_ticket(db: Session, admin: User, ticket_id: int, data: TicketUpdate) -> Ticket:
    ticket = get_ticket(db, admin, ticket_id)
    changes = data.model_dump(exclude_unset=True)

    if "status" in changes:
        _set_status(ticket, changes["status"])
    if "category" in changes and changes["category"] != ticket.category:
        ticket.category = changes["category"]
        ticket.category_source = FieldSource.ADMIN
        ticket.ai_draft = None  # the draft used the old category's policy
    if "priority" in changes:
        ticket.priority = changes["priority"]
        ticket.priority_source = FieldSource.ADMIN
    if "assigned_admin_id" in changes:
        ticket.assigned_admin_id = _validate_assignee(db, changes["assigned_admin_id"])

    db.commit()
    broker.publish(TicketEvent(EventType.TICKET_UPDATED, ticket.id, ticket.author_id))
    return get_ticket(db, admin, ticket.id)


def add_message(db: Session, user: User, ticket_id: int, data: MessageCreate) -> Ticket:
    ticket = get_ticket(db, user, ticket_id)
    is_admin = user.role == UserRole.ADMIN

    if not is_admin and (data.status is not None or data.used_ai_draft):
        raise ForbiddenError("Authors can't set status or AI-draft flags")
    if ticket.status == TicketStatus.CLOSED and not is_admin:
        raise ConflictError("This ticket is closed. Please raise a new ticket if you need more help.")

    ticket.messages.append(
        TicketMessage(sender_id=user.id, sender=user, body=data.body, used_ai_draft=is_admin and data.used_ai_draft)
    )
    ticket.ai_draft = None  # the thread moved on; the next draft must see this message

    if is_admin:
        ticket.awaiting_team_reply = False
        ticket.first_responded_at = ticket.first_responded_at or utcnow()
        if ticket.assigned_admin_id is None:
            ticket.assigned_admin_id = user.id  # whoever replies first owns it
        if data.status is not None:
            _set_status(ticket, data.status)
        elif ticket.status == TicketStatus.OPEN:
            _set_status(ticket, TicketStatus.IN_PROGRESS)
    else:
        ticket.awaiting_team_reply = True
        if ticket.status == TicketStatus.RESOLVED:
            _set_status(ticket, TicketStatus.OPEN)  # a follow-up reopens it for the team

    ticket.updated_at = utcnow()
    db.commit()
    broker.publish(TicketEvent(EventType.MESSAGE_ADDED, ticket.id, ticket.author_id))
    return get_ticket(db, user, ticket.id)


def add_note(db: Session, admin: User, ticket_id: int, body: str) -> Ticket:
    ticket = get_ticket(db, admin, ticket_id)
    ticket.internal_notes.append(InternalNote(admin_id=admin.id, admin=admin, body=body))
    db.commit()
    broker.publish(TicketEvent(EventType.NOTE_ADDED, ticket.id, ticket.author_id, admin_only=True))
    return get_ticket(db, admin, ticket.id)


def reset_triage(db: Session, admin: User, ticket_id: int) -> Ticket:
    """Hand category and priority back to the AI (clears admin overrides) and mark for re-triage."""
    ticket = get_ticket(db, admin, ticket_id)
    ticket.category_source = None
    ticket.priority_source = None
    ticket.ai_status = AIStatus.PENDING
    db.commit()
    broker.publish(TicketEvent(EventType.TICKET_UPDATED, ticket.id, ticket.author_id))
    return ticket


# --- Helpers ----------------------------------------------------------------------------


def _set_status(ticket: Ticket, status: TicketStatus) -> None:
    ticket.status = status
    if status in UNRESOLVED:
        ticket.resolved_at = None
    elif ticket.resolved_at is None:
        ticket.resolved_at = utcnow()
    if status in (TicketStatus.RESOLVED, TicketStatus.CLOSED):
        ticket.awaiting_team_reply = False


def _validate_assignee(db: Session, admin_id: int | None) -> int | None:
    if admin_id is None:
        return None
    assignee = db.get(User, admin_id)
    if assignee is None or assignee.role != UserRole.ADMIN:
        raise ValidationFailedError(
            "Tickets can only be assigned to BookLeaf team members",
            [{"field": "assigned_admin_id", "message": "Not an admin user"}],
        )
    return admin_id


def _start_of_day(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=timezone.utc)
