"""Turns database records into compact, factual prompt context.

The model is told to rely on these facts and never invent figures, so this is
where specific numbers and dates in a drafted reply come from. Only the book the
ticket is about is included (or a one-line summary per book for account-level
tickets), never the author's whole record.
"""

from datetime import date

from app.models import Author, Book, Ticket
from app.services.royalty import (
    MIN_PAYOUT_THRESHOLD,
    PAYOUT_WINDOW_DAYS,
    PayoutStatus,
    RoyaltySummary,
    royalty_summary,
)

_PAYOUT_STATUS_NOTES = {
    PayoutStatus.NOT_EARNING: "no royalties earned yet",
    PayoutStatus.PAID_UP: "fully paid, nothing pending",
    PayoutStatus.BELOW_THRESHOLD: (
        f"pending amount is below the ₹{MIN_PAYOUT_THRESHOLD:,} minimum and rolls over to the next quarter"
    ),
    PayoutStatus.SCHEDULED: "pending amount is due in the next payout run",
    PayoutStatus.POSSIBLY_OVERDUE: (
        "POSSIBLY OVERDUE: the book was selling before the last payout deadline passed, but there has been no "
        "payout since. Treat as BookLeaf's responsibility to investigate"
    ),
}


def _rupees(amount: int | None) -> str:
    return "n/a" if amount is None else f"₹{amount:,}"


def _fmt_date(value: date | None) -> str:
    return value.strftime("%d %b %Y") if value else "never"


def book_facts(book: Book, summary: RoyaltySummary) -> str:
    lines = [f'Book: "{book.title}" ({book.id}), ISBN {book.isbn}, genre {book.genre or "n/a"}']
    lines.append(f"Status: {book.status}")
    if not book.is_published:
        lines.append("Not yet published, so no sales or royalties yet. No print partner or listings assigned yet.")
        return "\n".join(lines)

    status = next(br.payout_status for br in summary.books if br.book.id == book.id)
    lines += [
        f"Published: {_fmt_date(book.publication_date)}; MRP {_rupees(book.mrp)}; "
        f"author royalty per copy {_rupees(book.author_royalty_per_copy)}",
        f"Copies sold: {book.total_copies_sold:,}; royalty earned {_rupees(book.total_royalty_earned)}, "
        f"paid {_rupees(book.royalty_paid)}, pending {_rupees(book.royalty_pending)}",
        f"Last royalty payout for this book: {_fmt_date(book.last_royalty_payout_date)}",
        f"Payout status: {_PAYOUT_STATUS_NOTES[status]}",
        f"Printed by: {book.print_partner or 'n/a'}",
        f"Listed on: {', '.join(book.available_on) if book.available_on else 'no platforms yet'}",
    ]
    return "\n".join(lines)


def account_facts(author: Author, books: list[Book], book: Book | None, today: date) -> str:
    """Facts for the drafting prompt."""
    summary = royalty_summary(books, today)
    lines = [
        f"Author: {author.name} (address them as {author.name.split()[0]}); author ID {author.id}; "
        f"with BookLeaf since {_fmt_date(author.joined_date)}",
        f"Today's date: {_fmt_date(today)}",
        f"Account royalty totals: pending {_rupees(summary.total_pending)} across {len(books)} book(s) "
        f"({'meets' if summary.meets_threshold else 'below'} the ₹{MIN_PAYOUT_THRESHOLD:,} payout threshold)",
        f"Next payout date: {_fmt_date(summary.next_payout_date)} "
        f"(payment for the quarter just ended, within {PAYOUT_WINDOW_DAYS} days)",
        "Bank details: not visible to the support system; ask the author to confirm they are linked in the dashboard "
        "if relevant.",
    ]
    if book is not None:
        lines += ["", "The ticket is about this book:", book_facts(book, summary)]
    else:
        lines += ["", "The ticket is account-level (no specific book). The author's books:"]
        lines += [f'- "{b.title}" ({b.id}): {b.status}, pending {_rupees(b.royalty_pending)}' for b in books]
    return "\n".join(lines)


def triage_facts(ticket: Ticket, today: date) -> str:
    """A one or two line version for classification, which only needs urgency signals."""
    if ticket.book is None:
        return "Account-level ticket (no specific book selected)."
    book = ticket.book
    if not book.is_published:
        return f'About "{book.title}": {book.status} (not yet published).'
    summary = royalty_summary(list(ticket.author.books), today)
    status = next(br.payout_status for br in summary.books if br.book.id == book.id)
    return (
        f'About "{book.title}": {book.status}, published {_fmt_date(book.publication_date)}, '
        f"royalty pending {_rupees(book.royalty_pending)}, last payout {_fmt_date(book.last_royalty_payout_date)} "
        f"({_PAYOUT_STATUS_NOTES[status]})."
    )


def truncate(text: str, limit: int) -> str:
    """Bound user-written text so one very long ticket can't blow up the token count."""
    text = text.strip()
    return text if len(text) <= limit else text[:limit].rstrip() + " [...truncated]"


