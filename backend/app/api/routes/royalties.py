from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import AuthorUser, DbSession
from app.core.config import get_settings
from app.models import Book
from app.schemas.book import BookRoyaltyOut, RoyaltySummaryOut
from app.services.royalty import MIN_PAYOUT_THRESHOLD, royalty_summary

router = APIRouter(prefix="/royalties", tags=["books"])


@router.get("/summary", response_model=RoyaltySummaryOut)
def my_royalty_summary(user: AuthorUser, db: DbSession):
    """The author's royalty totals, next payout date and per-book payout status."""
    books = list(db.scalars(select(Book).where(Book.author_id == user.author_id).order_by(Book.id)))
    summary = royalty_summary(books, get_settings().today())
    return RoyaltySummaryOut(
        total_earned=summary.total_earned,
        total_paid=summary.total_paid,
        total_pending=summary.total_pending,
        payout_threshold=MIN_PAYOUT_THRESHOLD,
        meets_threshold=summary.meets_threshold,
        next_payout_date=summary.next_payout_date,
        books=[
            BookRoyaltyOut(book_id=br.book.id, title=br.book.title, payout_status=br.payout_status)
            for br in summary.books
        ],
    )
