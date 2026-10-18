from datetime import date

from pydantic import BaseModel, ConfigDict

from app.services.royalty import PayoutStatus


class BookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    author_id: str
    title: str
    isbn: str
    genre: str | None
    publication_date: date | None
    status: str
    is_published: bool
    mrp: int | None
    author_royalty_per_copy: int | None
    total_copies_sold: int
    total_royalty_earned: int
    royalty_paid: int
    royalty_pending: int
    last_royalty_payout_date: date | None
    print_partner: str | None
    available_on: list[str]


class BookRoyaltyOut(BaseModel):
    book_id: str
    title: str
    payout_status: PayoutStatus


class RoyaltySummaryOut(BaseModel):
    total_earned: int
    total_paid: int
    total_pending: int
    payout_threshold: int
    meets_threshold: bool
    next_payout_date: date
    books: list[BookRoyaltyOut]
