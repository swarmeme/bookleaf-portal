"""Request and response models for tickets.

Authors and admins get different response models. The author versions simply
have no fields for priority, AI reasoning, assignment or internal notes, so
those can't leak through a serialisation mistake.
"""

from datetime import date, datetime
from typing import Generic, Self, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import AIStatus, FieldSource, TicketCategory, TicketPriority, TicketStatus, UserRole
from app.schemas.book import BookOut

T = TypeVar("T")


class _Input(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class _Output(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Requests -------------------------------------------------------------------


class TicketCreate(_Input):
    book_id: str | None = Field(default=None, description="Omit or null for a general / account-level query")
    subject: str = Field(min_length=5, max_length=200)
    description: str = Field(min_length=20, max_length=5000)
    attachment_name: str | None = Field(
        default=None, max_length=255, description="File name only; uploading the file itself is not implemented"
    )


class TicketUpdate(_Input):
    """Admin changes. Send only the fields to change; `assigned_admin_id: null` unassigns."""

    status: TicketStatus | None = None
    category: TicketCategory | None = None
    priority: TicketPriority | None = None
    assigned_admin_id: int | None = None

    @model_validator(mode="after")
    def check_fields(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update")
        for name in ("status", "category", "priority"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class MessageCreate(_Input):
    body: str = Field(min_length=1, max_length=5000)
    used_ai_draft: bool = Field(default=False, description="Admin only: the reply started from the AI draft")
    status: TicketStatus | None = Field(
        default=None, description="Admin only: also move the ticket to this status (e.g. send and resolve)"
    )


class NoteCreate(_Input):
    body: str = Field(min_length=1, max_length=5000)


# --- Shared pieces ------------------------------------------------------------------


class PersonOut(_Output):
    id: int
    name: str


class SenderOut(PersonOut):
    role: UserRole


class BookRef(_Output):
    id: str
    title: str
    status: str


class AuthorRef(_Output):
    id: str
    name: str
    email: str


class AuthorProfile(AuthorRef):
    phone: str | None
    city: str | None
    joined_date: date | None


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


# --- Author view --------------------------------------------------------------------


class AuthorMessageOut(_Output):
    id: int
    body: str
    created_at: datetime
    sender: SenderOut


class AuthorTicketSummary(_Output):
    id: int
    subject: str
    book: BookRef | None
    status: TicketStatus
    category: TicketCategory | None
    awaiting_team_reply: bool
    message_count: int
    created_at: datetime
    updated_at: datetime


class AuthorTicketDetail(AuthorTicketSummary):
    description: str
    attachment_name: str | None
    resolved_at: datetime | None
    messages: list[AuthorMessageOut]


# --- Admin view ---------------------------------------------------------------------


class AdminMessageOut(AuthorMessageOut):
    used_ai_draft: bool


class NoteOut(_Output):
    id: int
    body: str
    created_at: datetime
    admin: PersonOut


class AdminTicketSummary(_Output):
    id: int
    subject: str
    author: AuthorRef
    book: BookRef | None
    status: TicketStatus
    category: TicketCategory | None
    category_source: FieldSource | None
    priority: TicketPriority | None
    priority_source: FieldSource | None
    ai_status: AIStatus
    assigned_admin: PersonOut | None
    awaiting_team_reply: bool
    message_count: int
    created_at: datetime
    updated_at: datetime


class AdminTicketDetail(AdminTicketSummary):
    description: str
    attachment_name: str | None
    ai_reasoning: str | None
    first_responded_at: datetime | None
    resolved_at: datetime | None
    author: AuthorProfile
    book_details: BookOut | None = Field(validation_alias="book")
    messages: list[AdminMessageOut]
    internal_notes: list[NoteOut]


class TicketStats(BaseModel):
    """Counts for the admin queue header."""

    open: int
    in_progress: int
    resolved: int
    closed: int
    unassigned: int
    awaiting_reply: int
    critical_open: int
    pending_triage: int


class DraftOut(BaseModel):
    status: str  # generated | cached | unavailable
    draft: str | None
    generated_at: datetime | None
    message: str | None
