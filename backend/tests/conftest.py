"""Test setup: an isolated SQLite file per test and a fake LLM in place of Gemini."""

import os
import shutil
import tempfile
from pathlib import Path

# Configure before the app is imported: settings and the engine are created at import time.
_TMP = Path(tempfile.mkdtemp(prefix="bookleaf-tests-"))
_DB = _TMP / "test.db"
_TEMPLATE = _TMP / "template.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["GEMINI_API_KEY"] = ""
os.environ["AS_OF_DATE"] = "2026-01-20"
os.environ["JWT_SECRET"] = "test-secret-that-is-long-enough-for-hs256"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.ai.client import AIUnavailableError, LLMResult  # noqa: E402
from app.core.database import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.seed.seed import init_db  # noqa: E402

AUTHOR_PASSWORD = "author123"
ADMIN_PASSWORD = "admin123"


class FakeLLM:
    """Records every call. Responses are queued; an exception in the queue is raised instead."""

    def __init__(self):
        self.calls: list[dict] = []
        self.responses: list[str | Exception] = []

    def generate(self, **kwargs) -> LLMResult:
        self.calls.append(kwargs)
        response = self.responses.pop(0) if self.responses else AIUnavailableError("no fake response queued")
        if isinstance(response, Exception):
            raise response
        return LLMResult(text=response, model=kwargs["model"])


@pytest.fixture(scope="session", autouse=True)
def _template_db():
    # Migrate and seed once, then copy the file for each test (bcrypt makes seeding slow).
    init_db()
    engine.dispose()
    shutil.copy(_DB, _TEMPLATE)
    yield
    shutil.rmtree(_TMP, ignore_errors=True)


@pytest.fixture(autouse=True)
def fresh_db():
    engine.dispose()
    shutil.copy(_TEMPLATE, _DB)
    yield


@pytest.fixture
def fake_llm(monkeypatch) -> FakeLLM:
    llm = FakeLLM()
    monkeypatch.setattr("app.services.triage.get_llm", lambda: llm)
    monkeypatch.setattr("app.api.routes.admin.get_llm", lambda: llm)
    return llm


def _login(email: str, password: str) -> TestClient:
    # Not used as a context manager, so the app's startup hook (background triage thread) doesn't run.
    client = TestClient(app)
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return client


@pytest.fixture
def admin() -> TestClient:
    return _login("admin@bookleaf.com", ADMIN_PASSWORD)


@pytest.fixture
def kavita() -> TestClient:
    """Author with one book in production (BK015) and one with ₹850 pending (BK016)."""
    return _login("kavita.deshmukh@email.com", AUTHOR_PASSWORD)


@pytest.fixture
def priya() -> TestClient:
    return _login("priya.sharma@email.com", AUTHOR_PASSWORD)


@pytest.fixture
def anon() -> TestClient:
    return TestClient(app)
