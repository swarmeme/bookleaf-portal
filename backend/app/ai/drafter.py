"""AI-drafted replies for admins.

Cost controls:
- The draft is cached on the ticket and reused until something changes (a new
  message, a category change), so reopening a ticket is free.
- Only the knowledge-base section for the ticket's category is sent.
- Only the most recent few thread messages are sent, each truncated.
"""

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from sqlalchemy.orm import Session

from app.ai.client import AIUnavailableError, LLMClient
from app.ai.context import account_facts, truncate
from app.ai.knowledge_base import sections_for
from app.ai.prompts import DRAFT_SYSTEM, draft_prompt
from app.core.config import get_settings
from app.models import Ticket
from app.models.enums import UserRole
from app.models.types import utcnow

_MAX_DESCRIPTION_CHARS = 4000
_MAX_THREAD_MESSAGES = 4
_MAX_MESSAGE_CHARS = 800


class DraftStatus(StrEnum):
    GENERATED = "generated"
    CACHED = "cached"
    UNAVAILABLE = "unavailable"  # AI down or not configured: the admin writes the reply manually


@dataclass(frozen=True)
class DraftResult:
    status: DraftStatus
    text: str | None
    generated_at: datetime | None
    message: str | None = None


def get_draft(db: Session, ticket: Ticket, llm: LLMClient | None, today: date, regenerate: bool = False) -> DraftResult:
    if ticket.ai_draft and not regenerate:
        return DraftResult(DraftStatus.CACHED, ticket.ai_draft, ticket.ai_draft_generated_at)

    if llm is None:
        return DraftResult(
            DraftStatus.UNAVAILABLE, None, None, "AI drafting is not configured. Please write the reply manually."
        )

    settings = get_settings()
    try:
        result = llm.generate(
            model=settings.gemini_draft_model,
            system=DRAFT_SYSTEM,
            prompt=_build_prompt(ticket, today),
            max_output_tokens=1000,
            temperature=0.4,  # a little variety in wording, still grounded
        )
    except AIUnavailableError as exc:
        return DraftResult(
            DraftStatus.UNAVAILABLE, None, None, f"{exc.reason}. Please write the reply manually or try again shortly."
        )

    ticket.ai_draft = result.text
    ticket.ai_draft_generated_at = utcnow()
    db.commit()
    return DraftResult(DraftStatus.GENERATED, ticket.ai_draft, ticket.ai_draft_generated_at)


def _build_prompt(ticket: Ticket, today: date) -> str:
    author = ticket.author
    return draft_prompt(
        knowledge=sections_for(ticket.category),
        facts=account_facts(author, list(author.books), ticket.book, today),
        subject=ticket.subject,
        description=truncate(ticket.description, _MAX_DESCRIPTION_CHARS),
        conversation=_conversation(ticket),
    )


def _conversation(ticket: Ticket) -> str | None:
    recent = ticket.messages[-_MAX_THREAD_MESSAGES:]
    if not recent:
        return None
    lines = []
    if len(ticket.messages) > len(recent):
        lines.append(f"({len(ticket.messages) - len(recent)} earlier messages omitted)")
    for message in recent:
        speaker = "BookLeaf" if message.sender.role == UserRole.ADMIN else "Author"
        lines.append(f"[{speaker}, {message.created_at:%d %b %Y}] {truncate(message.body, _MAX_MESSAGE_CHARS)}")
    return "\n".join(lines)
