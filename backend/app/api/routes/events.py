"""Server-Sent Events stream for real-time ticket updates."""

import asyncio
import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.api.deps import authenticate
from app.core.database import SessionLocal
from app.models.enums import UserRole
from app.services.events import broker

router = APIRouter(tags=["events"])

_KEEPALIVE_SECONDS = 15


@router.get("/events", response_class=StreamingResponse)
async def stream_events(request: Request):
    """Stream `ticket.created`, `ticket.updated`, `ticket.message` and `ticket.note` events as SSE.

    Each event's data is `{"type", "ticket_id", "author_id"}`; clients refetch the ticket through the
    REST API. Authors only receive events for their own tickets (and never `ticket.note`)."""
    # Authenticate with a short-lived session instead of the request-scoped one, so a
    # long-lived stream doesn't hold a database connection open.
    with SessionLocal() as db:
        user = authenticate(request, db)
        author_id = user.author_id if user.role == UserRole.AUTHOR else None

    subscriber = broker.subscribe(author_id)

    async def event_stream():
        try:
            # Tell the browser to retry after 3s if the connection drops.
            yield "retry: 3000\n: connected\n\n"
            while True:
                try:
                    event = await asyncio.wait_for(subscriber.queue.get(), timeout=_KEEPALIVE_SECONDS)
                except TimeoutError:
                    # A comment line keeps proxies from closing an idle connection.
                    yield ": keep-alive\n\n"
                    continue
                yield f"event: {event.type}\ndata: {json.dumps(event.to_json_dict())}\n\n"
        finally:
            broker.unsubscribe(subscriber)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
