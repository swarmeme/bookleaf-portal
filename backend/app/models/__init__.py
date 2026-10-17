"""Import every model here so Base.metadata knows about all tables."""

from app.models.book import Book
from app.models.ticket import InternalNote, Ticket, TicketMessage
from app.models.user import Author, User

__all__ = ["Author", "Book", "InternalNote", "Ticket", "TicketMessage", "User"]
