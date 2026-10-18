"""Ticket triage: category + priority, by AI with a keyword fallback."""

import logging
from dataclasses import dataclass
from datetime import date

from pydantic import BaseModel, Field, ValidationError

from app.ai import fallback
from app.ai.client import AIUnavailableError, LLMClient
from app.ai.context import triage_facts, truncate
from app.ai.prompts import CLASSIFY_SYSTEM, classify_prompt
from app.core.config import get_settings
from app.models import Ticket
from app.models.enums import AIStatus, FieldSource, TicketCategory, TicketPriority

logger = logging.getLogger(__name__)

# Classification only needs the gist; the first ~1,500 characters are plenty and cap the cost.
_MAX_DESCRIPTION_CHARS = 1500


class AITriage(BaseModel):
    """The JSON shape Gemini is constrained to return."""

    category: TicketCategory
    priority: TicketPriority
    reasoning: str = Field(max_length=400)


@dataclass(frozen=True)
class TriageResult:
    category: TicketCategory
    priority: TicketPriority
    reasoning: str
    source: FieldSource
    ai_status: AIStatus


def triage_ticket(ticket: Ticket, llm: LLMClient | None, today: date) -> TriageResult:
    if llm is None:
        return _fallback(ticket, AIStatus.DISABLED)

    settings = get_settings()
    try:
        result = llm.generate(
            model=settings.gemini_classify_model,
            system=CLASSIFY_SYSTEM,
            prompt=classify_prompt(
                subject=ticket.subject,
                description=truncate(ticket.description, _MAX_DESCRIPTION_CHARS),
                facts=triage_facts(ticket, today),
            ),
            max_output_tokens=200,
            temperature=0.0,  # same ticket, same answer
            response_schema=AITriage,
        )
        try:
            parsed = AITriage.model_validate_json(result.text)
        except ValidationError as exc:
            raise AIUnavailableError("AI returned an invalid classification") from exc
    except AIUnavailableError:
        return _fallback(ticket, AIStatus.FAILED)

    return TriageResult(parsed.category, parsed.priority, parsed.reasoning.strip(), FieldSource.AI, AIStatus.COMPLETED)


def _fallback(ticket: Ticket, ai_status: AIStatus) -> TriageResult:
    rules = fallback.classify(ticket.subject, ticket.description)
    return TriageResult(rules.category, rules.priority, rules.reasoning, FieldSource.FALLBACK, ai_status)
