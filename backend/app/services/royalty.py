"""Royalty payout rules from the BookLeaf knowledge base, as code.

Royalties are calculated quarterly and paid within 45 days of the quarter ending.
Accumulated royalties below ₹1,000 roll over to the next quarter.

These facts feed both the author dashboard and the AI prompts, so the AI quotes
dates we computed instead of inventing them.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum

from app.models import Book

PAYOUT_WINDOW_DAYS = 45
MIN_PAYOUT_THRESHOLD = 1000  # rupees


class PayoutStatus(StrEnum):
    NOT_EARNING = "not_earning"  # still in production, or no sales yet
    PAID_UP = "paid_up"  # nothing pending
    BELOW_THRESHOLD = "below_threshold"  # pending, but the author's total is under ₹1,000
    SCHEDULED = "scheduled"  # pending and due in the next payout run
    POSSIBLY_OVERDUE = "possibly_overdue"  # a payout deadline passed without a payout for this book


def quarter_end_on_or_before(day: date) -> date:
    """The last calendar-quarter end date on or before `day`."""
    for month in (12, 9, 6, 3):
        end = _quarter_end(day.year, month)
        if end <= day:
            return end
    return _quarter_end(day.year - 1, 12)


def _quarter_end(year: int, month: int) -> date:
    next_month_first = date(year + (month == 12), month % 12 + 1, 1)
    return next_month_first - timedelta(days=1)


def _previous_quarter_end(quarter_end: date) -> date:
    return quarter_end_on_or_before(quarter_end.replace(day=1) - timedelta(days=1))


def next_payout_date(today: date) -> date:
    """Deadline of the next payout run that hasn't passed yet."""
    quarter_end = quarter_end_on_or_before(today)
    deadline = quarter_end + timedelta(days=PAYOUT_WINDOW_DAYS)
    if deadline >= today:
        return deadline
    following_end = quarter_end_on_or_before(quarter_end + timedelta(days=95))
    return following_end + timedelta(days=PAYOUT_WINDOW_DAYS)


def last_closed_cycle_quarter_end(today: date) -> date:
    """End of the most recent quarter whose 45-day payout window has fully passed."""
    quarter_end = quarter_end_on_or_before(today)
    while quarter_end + timedelta(days=PAYOUT_WINDOW_DAYS) >= today:
        quarter_end = _previous_quarter_end(quarter_end)
    return quarter_end


def book_payout_status(book: Book, author_pending_total: int, today: date) -> PayoutStatus:
    if not book.is_published or book.total_royalty_earned == 0:
        return PayoutStatus.NOT_EARNING
    if book.royalty_pending <= 0:
        return PayoutStatus.PAID_UP
    if author_pending_total < MIN_PAYOUT_THRESHOLD:
        return PayoutStatus.BELOW_THRESHOLD

    # Royalties earned up to `cycle_end` should have been paid out by now. A book that
    # was selling by then but hasn't had a payout since may be overdue. "Possibly",
    # because the data has no per-quarter breakdown: some of the pending amount may be
    # from the current quarter and legitimately not due yet.
    cycle_end = last_closed_cycle_quarter_end(today)
    selling_before_cycle_end = book.publication_date is not None and book.publication_date <= cycle_end
    no_payout_since = book.last_royalty_payout_date is None or book.last_royalty_payout_date < cycle_end
    if selling_before_cycle_end and no_payout_since:
        return PayoutStatus.POSSIBLY_OVERDUE
    return PayoutStatus.SCHEDULED


@dataclass(frozen=True)
class BookRoyalty:
    book: Book
    payout_status: PayoutStatus


@dataclass(frozen=True)
class RoyaltySummary:
    total_earned: int
    total_paid: int
    total_pending: int
    meets_threshold: bool
    next_payout_date: date
    books: list[BookRoyalty]


def royalty_summary(books: list[Book], today: date) -> RoyaltySummary:
    """Royalty position across all of one author's books (the threshold applies per author)."""
    total_pending = sum(b.royalty_pending for b in books)
    return RoyaltySummary(
        total_earned=sum(b.total_royalty_earned for b in books),
        total_paid=sum(b.royalty_paid for b in books),
        total_pending=total_pending,
        meets_threshold=total_pending >= MIN_PAYOUT_THRESHOLD,
        next_payout_date=next_payout_date(today),
        books=[BookRoyalty(b, book_payout_status(b, total_pending, today)) for b in books],
    )
