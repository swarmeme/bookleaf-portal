"""FastAPI application entry point: `uvicorn app.main:app`."""

import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from app.api.routes import auth, books
from app.core.errors import register_error_handlers
from app.seed.seed import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="BookLeaf Author Support Portal", lifespan=lifespan)
register_error_handlers(app)

api = APIRouter(prefix="/api")
api.include_router(auth.router)
api.include_router(books.router)


@api.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


app.include_router(api)
