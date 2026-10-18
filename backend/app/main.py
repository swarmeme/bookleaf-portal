"""FastAPI application entry point: `uvicorn app.main:app`."""

import logging
import threading
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import admin, auth, books, events, royalties, tickets
from app.core.config import get_settings
from app.core.errors import NotFoundError, register_error_handlers
from app.seed.seed import init_db
from app.services.triage import triage_pending_tickets

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    if not settings.ai_enabled:
        logger.warning("GEMINI_API_KEY not set: running in fallback mode (keyword triage, manual replies)")
    # Pick up tickets whose triage never ran (seed data, or a restart mid-task) without delaying startup.
    threading.Thread(target=triage_pending_tickets, name="triage-pending", daemon=True).start()
    yield


app = FastAPI(
    title="BookLeaf Author Support Portal",
    description="REST API for the author portal and the BookLeaf support team's admin portal.",
    version="1.0.0",
    lifespan=lifespan,
)
register_error_handlers(app)

api = APIRouter(prefix="/api")
api.include_router(auth.router)
api.include_router(books.router)
api.include_router(royalties.router)
api.include_router(tickets.router)
api.include_router(admin.router)
api.include_router(events.router)


@api.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "ai_enabled": settings.ai_enabled}


@api.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
def api_not_found(path: str):
    # Without this, unknown /api paths would fall through to the frontend's index.html below.
    raise NotFoundError(f"No API endpoint at /api/{path}")


app.include_router(api)

# Serve the built frontend (frontend/dist) from the same server when it exists, so the whole
# app runs on one port. In development, Vite serves the frontend and proxies /api here instead.
if settings.frontend_dist_dir.is_dir():
    index_html = settings.frontend_dist_dir / "index.html"
    app.mount("/assets", StaticFiles(directory=settings.frontend_dist_dir / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        # Client-side routes (/tickets/5 etc.) all load the single-page app.
        file = (settings.frontend_dist_dir / path).resolve()
        if path and file.is_file() and file.is_relative_to(settings.frontend_dist_dir.resolve()):
            return FileResponse(file)
        return FileResponse(index_html)
