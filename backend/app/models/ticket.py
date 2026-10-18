from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import AIStatus, FieldSource, TicketCategory, TicketPriority, TicketStatus
from app.models.types import UTCDateTime, enum_column, utcnow


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[str] = mapped_column(ForeignKey("authors.id"), index=True)
    book_id: Mapped[str | None] = mapped_column(ForeignKey("books.id"))  # None = general / account level
    subject: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    attachment_name: Mapped[str | None] = mapped_column(String(255))  # file name only; upload is out of scope

    status: Mapped[TicketStatus] = mapped_column(enum_column(TicketStatus), default=TicketStatus.OPEN, index=True)
    assigned_admin_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    # True while the ball is in BookLeaf's court: set on creation and on author
    # follow-ups, cleared when the team replies. Drives the queue's "needs reply" flag.
    awaiting_team_reply: Mapped[bool] = mapped_column(default=True, index=True)

    # Triage. Nullable until classification has run (it runs after the ticket is saved).
    category: Mapped[TicketCategory | None] = mapped_column(enum_column(TicketCategory), index=True)
    category_source: Mapped[FieldSource | None] = mapped_column(enum_column(FieldSource))
    priority: Mapped[TicketPriority | None] = mapped_column(enum_column(TicketPriority), index=True)
    priority_source: Mapped[FieldSource | None] = mapped_column(enum_column(FieldSource))
    ai_status: Mapped[AIStatus] = mapped_column(enum_column(AIStatus), default=AIStatus.PENDING)
    ai_reasoning: Mapped[str | None] = mapped_column(Text)  # one-line "why this priority", shown to admins

    # Cached AI draft reply, so reopening a ticket doesn't cost another AI call.
    ai_draft: Mapped[str | None] = mapped_column(Text)
    ai_draft_generated_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)
    first_responded_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    resolved_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    author: Mapped["Author"] = relationship()
    book: Mapped["Book | None"] = relationship()
    assigned_admin: Mapped["User | None"] = relationship()
    messages: Mapped[list["TicketMessage"]] = relationship(
        back_populates="ticket", order_by="TicketMessage.created_at", cascade="all, delete-orphan"
    )
    internal_notes: Mapped[list["InternalNote"]] = relationship(
        back_populates="ticket", order_by="InternalNote.created_at", cascade="all, delete-orphan"
    )

    @property
    def message_count(self) -> int:
        return len(self.messages)


class TicketMessage(Base):
    """A message in the author-visible thread: a team reply or an author follow-up."""

    __tablename__ = "ticket_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), index=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    # True when an admin sent a reply that started from the AI draft. Lets the team
    # measure how often drafts are actually useful.
    used_ai_draft: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    ticket: Mapped[Ticket] = relationship(back_populates="messages")
    sender: Mapped["User"] = relationship()


class InternalNote(Base):
    """Admin-only note. Kept in its own table so author-facing queries can never include one."""

    __tablename__ = "internal_notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), index=True)
    admin_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    ticket: Mapped[Ticket] = relationship(back_populates="internal_notes")
    admin: Mapped["User"] = relationship()

