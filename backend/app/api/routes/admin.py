"""Admin (BookLeaf team) endpoints: the ticket queue, triage, replies, notes and AI drafts."""

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, BackgroundTasks, Query, status
from sqlalchemy import select

from app.ai.client import get_llm
from app.ai.drafter import get_draft
from app.api.deps import AdminUser, DbSession
from app.core.config import get_settings
from app.models import User
from app.models.enums import TicketCategory, TicketPriority, TicketStatus, UserRole
from app.schemas.ticket import (
    AdminTicketDetail,
    AdminTicketSummary,
    DraftOut,
    MessageCreate,
    NoteCreate,
    Page,
    PersonOut,
    TicketStats,
    TicketUpdate,
)
from app.services import tickets as ticket_service
from app.services.triage import triage_in_background

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/tickets", response_model=Page[AdminTicketSummary])
def list_tickets(
    admin: AdminUser,
    db: DbSession,
    status_: Annotated[list[TicketStatus] | None, Query(alias="status")] = None,
    category: Annotated[list[TicketCategory] | None, Query()] = None,
    priority: Annotated[list[TicketPriority] | None, Query()] = None,
    assigned: Annotated[Literal["me", "unassigned"] | None, Query()] = None,
    awaiting_reply: bool | None = None,
    book_id: str | None = None,
    created_from: date | None = None,
    created_to: date | None = None,
    q: Annotated[str | None, Query(max_length=100, description="Search subject and description")] = None,
    sort: Literal["urgency", "newest", "oldest", "updated"] = "urgency",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
):
    """The ticket queue across all authors. The default `urgency` sort puts unresolved tickets first,
    then critical > high > untriaged > medium > low, then oldest first."""
    filters = ticket_service.TicketFilters(
        status=status_,
        category=category,
        priority=priority,
        assigned=assigned,
        awaiting_reply=awaiting_reply,
        book_id=book_id,
        created_from=created_from,
        created_to=created_to,
        search=q,
        sort=sort,
    )
    items, total = ticket_service.list_tickets(db, admin, filters, page, page_size)
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/tickets/stats", response_model=TicketStats)
def ticket_stats(_admin: AdminUser, db: DbSession):
    return ticket_service.ticket_stats(db)


@router.get("/tickets/{ticket_id}", response_model=AdminTicketDetail)
def get_ticket(ticket_id: int, admin: AdminUser, db: DbSession):
    return ticket_service.get_ticket(db, admin, ticket_id)


@router.patch("/tickets/{ticket_id}", response_model=AdminTicketDetail)
def update_ticket(ticket_id: int, body: TicketUpdate, admin: AdminUser, db: DbSession):
    """Change status, override category/priority, or (un)assign. Overrides are marked `source: admin`
    and are never overwritten by a later AI triage."""
    return ticket_service.update_ticket(db, admin, ticket_id, body)


@router.post("/tickets/{ticket_id}/messages", response_model=AdminTicketDetail, status_code=status.HTTP_201_CREATED)
def reply(ticket_id: int, body: MessageCreate, admin: AdminUser, db: DbSession):
    """Send a reply the author will see. Optionally set the status in the same step (e.g. resolve)."""
    return ticket_service.add_message(db, admin, ticket_id, body)


@router.post("/tickets/{ticket_id}/notes", response_model=AdminTicketDetail, status_code=status.HTTP_201_CREATED)
def add_note(ticket_id: int, body: NoteCreate, admin: AdminUser, db: DbSession):
    """Internal note. Never visible to the author."""
    return ticket_service.add_note(db, admin, ticket_id, body.body)


@router.post("/tickets/{ticket_id}/draft", response_model=DraftOut)
def draft_reply(ticket_id: int, admin: AdminUser, db: DbSession, regenerate: bool = False):
    """AI-drafted reply grounded in the knowledge base and the author's account data.

    Returns the cached draft unless `regenerate=true` or the ticket changed since it was drafted.
    If the AI is unavailable the response is still 200, with `status: "unavailable"` and no draft,
    so the admin can carry on and write the reply by hand."""
    ticket = ticket_service.get_ticket(db, admin, ticket_id)
    result = get_draft(db, ticket, get_llm(), get_settings().today(), regenerate=regenerate)
    return DraftOut(status=result.status, draft=result.text, generated_at=result.generated_at, message=result.message)


@router.post("/tickets/{ticket_id}/triage", response_model=AdminTicketDetail, status_code=status.HTTP_202_ACCEPTED)
def retriage(ticket_id: int, admin: AdminUser, db: DbSession, background: BackgroundTasks):
    """Re-run AI triage (e.g. after an AI outage). Clears manual overrides on category and priority."""
    ticket = ticket_service.reset_triage(db, admin, ticket_id)
    background.add_task(triage_in_background, ticket.id)
    return ticket_service.get_ticket(db, admin, ticket_id)


@router.get("/team", response_model=list[PersonOut])
def list_team(_admin: AdminUser, db: DbSession):
    """BookLeaf team members, for assignment."""
    return db.scalars(select(User).where(User.role == UserRole.ADMIN).order_by(User.name)).all()

