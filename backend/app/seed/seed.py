"""Load the provided sample dataset plus demo admin accounts.

Runs automatically on startup when the database is empty. To wipe and reseed:

    python -m app.seed.seed --reset
"""

import argparse
import json
import logging
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models import Author, Book, User
from app.models.enums import UserRole

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

    db.commit()
    logger.info("Seeded %d authors and %d admins", len(data["authors"]), len(DEMO_ADMINS))


def init_db() -> None:
    """Create tables and seed them if the database is empty. Safe to call on every startup."""
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if db.scalar(select(User.id).limit(1)) is None:
            seed(db)


def reset_db() -> None:
    Base.metadata.drop_all(engine)
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
