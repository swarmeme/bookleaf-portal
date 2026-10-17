from datetime import date

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

PUBLISHED_STATUS = "Published & Live"


class Book(Base):
    """A title in the catalogue. Money fields are whole rupees, matching the source data.

    Books still in production have no publication date, MRP or royalty rate yet,
    so those columns are nullable.
    """

    __tablename__ = "books"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)  # e.g. "BK001"
    author_id: Mapped[str] = mapped_column(ForeignKey("authors.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    isbn: Mapped[str] = mapped_column(String(32))
    genre: Mapped[str | None] = mapped_column(String(128))
    publication_date: Mapped[date | None]
    status: Mapped[str] = mapped_column(String(64))
    mrp: Mapped[int | None]
    author_royalty_per_copy: Mapped[int | None]
    total_copies_sold: Mapped[int] = mapped_column(default=0)
    total_royalty_earned: Mapped[int] = mapped_column(default=0)
    royalty_paid: Mapped[int] = mapped_column(default=0)
    royalty_pending: Mapped[int] = mapped_column(default=0)
    last_royalty_payout_date: Mapped[date | None]
    print_partner: Mapped[str | None] = mapped_column(String(64))
    available_on: Mapped[list[str]] = mapped_column(JSON, default=list)

    author: Mapped["Author"] = relationship(back_populates="books")

    @property
    def is_published(self) -> bool:
        return self.status == PUBLISHED_STATUS
