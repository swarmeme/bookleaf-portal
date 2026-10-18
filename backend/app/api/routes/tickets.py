"""Author-facing ticket endpoints. Every query is scoped to the logged-in author."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Query, status

from app.api.deps import AuthorUser, DbSession
from app.models.enums import TicketStatus
from app.schemas.ticket import AuthorTicketDetail, AuthorTicketSummary, MessageCreate, Page, TicketCreate
from app.services import tickets as ticket_service
from app.services.triage import triage_in_background

router = APIRouter(prefix="/tickets", tags=["author tickets"])


@router.get("", response_model=Page[AuthorTicketSummary])
def list_my_tickets(
    user: AuthorUser,
    db: DbSession,
    status_: Annotated[list[TicketStatus] | None, Query(alias="status")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
):
    """The author's own tickets, most recently updated first."""
    filters = ticket_service.TicketFilters(status=status_, sort="updated")
    items, total = ticket_service.list_tickets(db, user, filters, page, page_size)
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=AuthorTicketDetail, status_code=status.HTTP_201_CREATED)
def create_ticket(body: TicketCreate, user: AuthorUser, db: DbSession, background: BackgroundTasks):
    """Raise a ticket. It is saved and returned immediately; AI triage runs afterwards in the background,
    so ticket creation never depends on the AI being up."""
    ticket = ticket_service.create_ticket(db, user, body)
    background.add_task(triage_in_background, ticket.id)
    return ticket


@router.get("/{ticket_id}", response_model=AuthorTicketDetail)
def get_my_ticket(ticket_id: int, user: AuthorUser, db: DbSession):
    return ticket_service.get_ticket(db, user, ticket_id)


@router.post("/{ticket_id}/messages", response_model=AuthorTicketDetail, status_code=status.HTTP_201_CREATED)
def reply_to_ticket(ticket_id: int, body: MessageCreate, user: AuthorUser, db: DbSession):
    """Add a follow-up to the thread. A follow-up on a resolved ticket reopens it."""
    return ticket_service.add_message(db, user, ticket_id, body)
