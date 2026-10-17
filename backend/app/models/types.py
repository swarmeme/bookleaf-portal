"""Column types and helpers shared by the models."""

from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import DateTime, Enum, TypeDecorator


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """Stores UTC and always returns timezone-aware datetimes.

    SQLite has no timezone support and hands back naive datetimes, which would
    serialise without an offset and be misread as local time by browsers.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None and value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value


def enum_column(enum_cls: type[StrEnum]) -> Enum:
    """Store enum *values* (e.g. "in_progress") as plain strings, portable across databases."""
    return Enum(
        enum_cls,
        native_enum=False,
        values_callable=lambda members: [m.value for m in members],
        length=32,
        validate_strings=True,
    )
