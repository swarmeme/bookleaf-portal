"""Runs AI triage for tickets outside the request that created them.

Ticket creation never waits on the AI: the ticket is saved first and returned to
the author straight away, then triaged here in the background.
"""

import logging

from sqlalchemy import select

from app.ai.classifier import triage_ticket
from app.ai.client import get_llm
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models import Ticket
from app.models.enums import AIStatus, FieldSource
from app.services.events import EventType, TicketEvent, broker

logger = logging.getLogger(__name__)


def triage_in_background(ticket_id: int) -> None:
    """Entry point for FastAPI BackgroundTasks. Opens its own session; must never raise."""
    try:
        with SessionLocal() as db:
            ticket = db.get(Ticket, ticket_id)
            if ticket is None:
                return
            result = triage_ticket(ticket, get_llm(), get_settings().today())

            # An admin may have overridden a field while the AI was working; keep their choice.
            if ticket.category_source != FieldSource.ADMIN:
                ticket.category = result.category
                ticket.category_source = result.source
            if ticket.priority_source != FieldSource.ADMIN:
                ticket.priority = result.priority
                ticket.priority_source = result.source
            ticket.ai_reasoning = result.reasoning
            ticket.ai_status = result.ai_status
            db.commit()
            broker.publish(TicketEvent(EventType.TICKET_UPDATED, ticket.id, ticket.author_id))
    except Exception:
        logger.exception("Background triage failed for ticket %s", ticket_id)


def triage_pending_tickets() -> None:
    """Triage tickets left pending, e.g. because the server restarted before their background task ran."""
    with SessionLocal() as db:
        pending_ids = db.scalars(select(Ticket.id).where(Ticket.ai_status == AIStatus.PENDING)).all()
    if pending_ids:
        logger.info("Triaging %d pending ticket(s)", len(pending_ids))
    for ticket_id in pending_ids:
        triage_in_background(ticket_id)
