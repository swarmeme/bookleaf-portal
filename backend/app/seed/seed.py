"""Apply migrations, then load the provided sample dataset, demo admin accounts and
a handful of demo tickets.

Runs automatically on startup when the database is empty. To wipe and reseed:

    python -m app.seed.seed --reset
"""

import argparse
import json
import logging
from datetime import date, timedelta
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import BACKEND_DIR
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import Author, Book, InternalNote, Ticket, TicketMessage, User
from app.models.enums import TicketStatus, UserRole
from app.models.types import utcnow

logger = logging.getLogger(__name__)

DATA_FILE = Path(__file__).parent / "bookleaf_sample_data.json"

# Demo credentials, documented in the README.
AUTHOR_DEMO_PASSWORD = "author123"
ADMIN_DEMO_PASSWORD = "admin123"
DEMO_ADMINS = [
    ("Aarav Mehta", "admin@bookleaf.com"),
    ("Neha Verma", "ops@bookleaf.com"),
]


def _parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def seed(db: Session) -> None:
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    # Hash once and reuse: bcrypt is deliberately slow and every demo account shares a password.
    author_hash = hash_password(AUTHOR_DEMO_PASSWORD)
    admin_hash = hash_password(ADMIN_DEMO_PASSWORD)

    for name, email in DEMO_ADMINS:
        db.add(User(name=name, email=email, password_hash=admin_hash, role=UserRole.ADMIN))

    for raw_author in data["authors"]:
        user = User(
            name=raw_author["name"],
            email=raw_author["email"].lower(),
            password_hash=author_hash,
            role=UserRole.AUTHOR,
        )
        author = Author(
            id=raw_author["author_id"],
            user=user,
            phone=raw_author.get("phone"),
            city=raw_author.get("city"),
            joined_date=_parse_date(raw_author.get("joined_date")),
        )
        for raw_book in raw_author["books"]:
            author.books.append(
                Book(
                    id=raw_book["book_id"],
                    title=raw_book["title"],
                    isbn=raw_book["isbn"],
                    genre=raw_book.get("genre"),
                    publication_date=_parse_date(raw_book.get("publication_date")),
                    status=raw_book["status"],
                    mrp=raw_book.get("mrp"),
                    author_royalty_per_copy=raw_book.get("author_royalty_per_copy"),
                    total_copies_sold=raw_book.get("total_copies_sold") or 0,
                    total_royalty_earned=raw_book.get("total_royalty_earned") or 0,
                    royalty_paid=raw_book.get("royalty_paid") or 0,
                    royalty_pending=raw_book.get("royalty_pending") or 0,
                    last_royalty_payout_date=_parse_date(raw_book.get("last_royalty_payout_date")),
                    print_partner=raw_book.get("print_partner"),
                    available_on=raw_book.get("available_on") or [],
                )
            )
        db.add(author)

    db.flush()
    _seed_demo_tickets(db)
    db.commit()
    logger.info("Seeded %d authors, %d admins and demo tickets", len(data["authors"]), len(DEMO_ADMINS))


# Realistic queries so both portals have something to show on first run. They are left
# untriaged (ai_status=pending) and triaged on startup, through the same AI pipeline as new tickets.
# (author email, book id or None, subject, description, age, status)
_DEMO_TICKETS = [
    (
        "ananya.reddy@email.com", "BK005", "No royalty received since my book was published",
        "My book Between Two Temples was published in July 2024 and I have still not received a single royalty "
        "payment. The dashboard shows sales, so where is my money? It has been well over a year now.",
        timedelta(days=3), TicketStatus.OPEN,
    ),
    (
        "rohit.kapoor@email.com", "BK003", "Different ISBN on Amazon vs printed copy",
        "The ISBN shown on the Amazon listing for Code & Karma does not match the ISBN printed on the back cover "
        "of my author copies. Readers are messaging me asking if they bought the right book.",
        timedelta(days=2), TicketStatus.IN_PROGRESS,
    ),
    (
        "kavita.deshmukh@email.com", "BK015", "Raising Roots stuck in typesetting?",
        "It has been 3 weeks and my book Raising Roots still shows as in typesetting. When will it be done? "
        "I was hoping to launch it before the school holidays.",
        timedelta(days=1), TicketStatus.OPEN,
    ),
    (
        "priya.sharma@email.com", "BK001", "Royalty amount seems too low",
        "I have sold 342 copies of Whispers of the Ganges but the royalty I have received so far feels low "
        "for that many copies. Can you explain how it is calculated?",
        timedelta(hours=5), TicketStatus.OPEN,
    ),
    (
        "vikram.joshi@email.com", "BK007", "The Last Monsoon showing 'Currently Unavailable' on Amazon",
        "My poetry collection The Last Monsoon is showing as Currently Unavailable on Amazon India since last "
        "week. A few readers told me they could not order it.",
        timedelta(days=6), TicketStatus.RESOLVED,
    ),
    (
        "meera.nair@email.com", None, "Can I update my author bio?",
        "Hi, I would like to update my author bio on my book pages to mention my new book. "
        "Can I do that myself or does the team need to do it?",
        timedelta(minutes=40), TicketStatus.OPEN,
    ),
]


def _seed_demo_tickets(db: Session) -> None:
    users = {u.email: u for u in db.scalars(select(User))}
    admin = users[DEMO_ADMINS[0][1]]
    now = utcnow()
    tickets = {}
    for email, book_id, subject, description, age, status in _DEMO_TICKETS:
        created = now - age
        ticket = Ticket(
            author_id=users[email].author_id,
            book_id=book_id,
            subject=subject,
            description=description,
            status=status,
            created_at=created,
            updated_at=created,
        )
        db.add(ticket)
        tickets[book_id] = ticket

    isbn_ticket = tickets["BK003"]
    isbn_ticket.assigned_admin_id = admin.id
    isbn_ticket.internal_notes.append(
        InternalNote(
            admin_id=admin.id,
            body="Checked Amazon: listing shows -03-X instead of -03-5. Raised with production, awaiting fix.",
            created_at=now - timedelta(days=1, hours=20),
        )
    )

    resync_ticket = tickets["BK007"]
    replied_at = now - timedelta(days=5, hours=22)
    resync_ticket.assigned_admin_id = admin.id
    resync_ticket.awaiting_team_reply = False
    resync_ticket.first_responded_at = replied_at
    resync_ticket.resolved_at = replied_at
    resync_ticket.updated_at = replied_at
    resync_ticket.messages.append(
        TicketMessage(
            sender_id=admin.id,
            created_at=replied_at,
            body=(
                "Hi Vikram,\n\nThank you for flagging this, and I'm sorry readers couldn't order The Last Monsoon. "
                "This is a stock sync issue between our warehouse and Amazon India, not a problem with your listing. "
                "I've triggered a re-sync with our distribution team; it usually takes 24-48 hours for the book to "
                "show as available again.\n\nIf it still shows as unavailable after Thursday, just reply here and "
                "I'll escalate it straight away.\n\nWarm regards,\nBookLeaf Author Support"
            ),
        )
    )


def _alembic_config() -> Config:
    config = Config(BACKEND_DIR / "alembic.ini")
    config.attributes["configure_logger"] = False  # keep the app's logging setup
    return config


def init_db() -> None:
    """Apply migrations and seed if the database is empty. Safe to call on every startup."""
    command.upgrade(_alembic_config(), "head")
    with SessionLocal() as db:
        if db.scalar(select(User.id).limit(1)) is None:
            seed(db)


def reset_db() -> None:
    command.downgrade(_alembic_config(), "base")
    init_db()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Create and seed the database.")
    parser.add_argument("--reset", action="store_true", help="drop all data and reseed from scratch")
    args = parser.parse_args()
    if args.reset:
        reset_db()
    else:
        init_db()
