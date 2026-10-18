"""Enumerations shared by models, schemas and the AI layer.

Values are stable machine-readable slugs; the frontend maps them to labels.
"""

from enum import StrEnum


class UserRole(StrEnum):
    AUTHOR = "author"
    ADMIN = "admin"


class TicketStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketCategory(StrEnum):
    ROYALTY_PAYMENTS = "royalty_payments"
    ISBN_METADATA = "isbn_metadata"
    PRINTING_QUALITY = "printing_quality"
    DISTRIBUTION_AVAILABILITY = "distribution_availability"
    BOOK_STATUS_PRODUCTION = "book_status_production"
    GENERAL_INQUIRY = "general_inquiry"


class TicketPriority(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FieldSource(StrEnum):
    """Who set a ticket's category/priority. Lets admins see what to double-check."""

    AI = "ai"
    FALLBACK = "fallback"  # keyword rules, used when the AI is unavailable
    ADMIN = "admin"  # manual override


class AIStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"  # AI call failed; fallback values were used
    DISABLED = "disabled"  # no API key configured; fallback values were used

