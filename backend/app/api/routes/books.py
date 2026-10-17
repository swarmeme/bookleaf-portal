from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.errors import NotFoundError
from app.models import Book
from app.models.enums import UserRole
from app.schemas.book import BookOut

router = APIRouter(prefix="/books", tags=["books"])


@router.get("", response_model=list[BookOut])
def list_books(user: CurrentUser, db: DbSession, author_id: str | None = None):
    """Authors get their own books. Admins get every book, optionally filtered by author."""
    query = select(Book).order_by(Book.id)
    if user.role == UserRole.AUTHOR:
        query = query.where(Book.author_id == user.author_id)
    elif author_id:
        query = query.where(Book.author_id == author_id)
    return db.scalars(query).all()


@router.get("/{book_id}", response_model=BookOut)
def get_book(book_id: str, user: CurrentUser, db: DbSession):
    book = db.get(Book, book_id)
    # Another author's book is reported as "not found" rather than "forbidden",
    # so authors can't probe which book IDs exist.
    if book is None or (user.role == UserRole.AUTHOR and book.author_id != user.author_id):
        raise NotFoundError("Book not found")
    return book
