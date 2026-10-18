import asyncio
from datetime import date

import pytest

from app.core.database import SessionLocal
from app.models import Author
from app.services.events import EventBroker, EventType, TicketEvent
from app.services.royalty import PayoutStatus, last_closed_cycle_quarter_end, next_payout_date, royalty_summary

TODAY = date(2026, 1, 20)


@pytest.mark.parametrize(
    ("today", "expected"),
    [
        (date(2026, 1, 20), date(2026, 2, 14)),  # Q4 2025 payout window still open
        (date(2026, 2, 14), date(2026, 2, 14)),  # deadline day itself
        (date(2026, 2, 15), date(2026, 5, 15)),  # missed it: next is Q1 2026
        (date(2026, 3, 31), date(2026, 5, 15)),
        (date(2026, 9, 30), date(2026, 11, 14)),
    ],
)
def test_next_payout_date(today, expected):
    assert next_payout_date(today) == expected


def test_last_closed_cycle():
    assert last_closed_cycle_quarter_end(TODAY) == date(2025, 9, 30)


@pytest.mark.parametrize(
    ("author_id", "expected"),
    [
        ("AUTH001", {"BK001": PayoutStatus.SCHEDULED, "BK002": PayoutStatus.PAID_UP}),  # paid 15 Oct for Q3
        ("AUTH003", {"BK005": PayoutStatus.POSSIBLY_OVERDUE}),  # never paid since July 2024
        ("AUTH009", {"BK015": PayoutStatus.NOT_EARNING, "BK016": PayoutStatus.BELOW_THRESHOLD}),  # ₹850 < ₹1,000
        ("AUTH007", {"BK013": PayoutStatus.NOT_EARNING}),  # in production
    ],
)
def test_payout_status_on_sample_data(author_id, expected):
    with SessionLocal() as db:
        books = list(db.get(Author, author_id).books)
        statuses = {br.book.id: br.payout_status for br in royalty_summary(books, TODAY).books}
    assert {k: statuses[k] for k in expected} == expected


def test_broker_only_delivers_events_a_subscriber_may_see():
    async def scenario():
        broker = EventBroker()
        admin = broker.subscribe(author_id=None)
        author = broker.subscribe(author_id="AUTH001")
        broker.publish(TicketEvent(EventType.TICKET_UPDATED, 1, "AUTH001"))
        broker.publish(TicketEvent(EventType.TICKET_UPDATED, 2, "AUTH002"))  # someone else's ticket
        broker.publish(TicketEvent(EventType.NOTE_ADDED, 1, "AUTH001", admin_only=True))
        await asyncio.sleep(0)  # let call_soon_threadsafe callbacks run
        return admin.queue.qsize(), [author.queue.get_nowait().ticket_id for _ in range(author.queue.qsize())]

    admin_count, author_ticket_ids = asyncio.run(scenario())
    assert admin_count == 3
    assert author_ticket_ids == [1]
