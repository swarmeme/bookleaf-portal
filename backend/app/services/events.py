"""In-process publish/subscribe for real-time ticket updates (served over SSE).

Events are small notifications ("ticket 12 changed"); clients refetch through the
normal REST endpoints, so permission checks stay in one place. Each subscriber
only receives events it is allowed to see: authors get events for their own
tickets and never internal-note events; admins get everything.

This lives in one process's memory, which fits a single-server deployment. With
several API workers it would be swapped for Redis pub/sub or Postgres
LISTEN/NOTIFY behind the same publish()/subscribe() interface.
"""

import asyncio
import logging
import threading
from dataclasses import asdict, dataclass
from enum import StrEnum

logger = logging.getLogger(__name__)


class EventType(StrEnum):
    TICKET_CREATED = "ticket.created"
    TICKET_UPDATED = "ticket.updated"  # status, triage, assignment
    MESSAGE_ADDED = "ticket.message"
    NOTE_ADDED = "ticket.note"  # admin-only


@dataclass(frozen=True)
class TicketEvent:
    type: EventType
    ticket_id: int
    author_id: str
    admin_only: bool = False

    def to_json_dict(self) -> dict:
        data = asdict(self)
        del data["admin_only"]
        return data


@dataclass(eq=False)
class Subscriber:
    queue: asyncio.Queue
    loop: asyncio.AbstractEventLoop
    author_id: str | None  # None for admins (see every ticket)

    def can_see(self, event: TicketEvent) -> bool:
        if self.author_id is None:
            return True
        return not event.admin_only and event.author_id == self.author_id


class EventBroker:
    def __init__(self) -> None:
        self._subscribers: set[Subscriber] = set()
        self._lock = threading.Lock()

    def subscribe(self, author_id: str | None) -> Subscriber:
        subscriber = Subscriber(asyncio.Queue(maxsize=100), asyncio.get_running_loop(), author_id)
        with self._lock:
            self._subscribers.add(subscriber)
        return subscriber

    def unsubscribe(self, subscriber: Subscriber) -> None:
        with self._lock:
            self._subscribers.discard(subscriber)

    def publish(self, event: TicketEvent) -> None:
        """Safe to call from any thread (request handlers and background tasks run in a threadpool)."""
        with self._lock:
            targets = [s for s in self._subscribers if s.can_see(event)]
        for subscriber in targets:
            try:
                subscriber.loop.call_soon_threadsafe(_offer, subscriber.queue, event)
            except RuntimeError:  # the subscriber's event loop has closed
                self.unsubscribe(subscriber)


def _offer(queue: asyncio.Queue, event: TicketEvent) -> None:
    try:
        queue.put_nowait(event)
    except asyncio.QueueFull:
        # A stalled client. Dropping is safe: the client refetches on its next event or reconnect.
        logger.debug("Dropping event for a slow subscriber")


broker = EventBroker()
