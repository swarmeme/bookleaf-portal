from datetime import date, datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import UserRole
from app.models.types import UTCDateTime, enum_column, utcnow


class User(Base):
    """A login identity. Authors and admins share this table and differ by role."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(enum_column(UserRole))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    author: Mapped["Author | None"] = relationship(back_populates="user", uselist=False)

    @property
    def author_id(self) -> str | None:
        return self.author.id if self.author else None


class Author(Base):
    """Author profile, keyed by BookLeaf's own author ID (e.g. "AUTH001")."""

    __tablename__ = "authors"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    phone: Mapped[str | None] = mapped_column(String(32))
    city: Mapped[str | None] = mapped_column(String(128))
    joined_date: Mapped[date | None]

    user: Mapped[User] = relationship(back_populates="author")
    books: Mapped[list["Book"]] = relationship(back_populates="author", order_by="Book.id")

    @property
    def name(self) -> str:
        return self.user.name

    @property
    def email(self) -> str:
        return self.user.email
