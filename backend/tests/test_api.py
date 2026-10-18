"""Auth, role-based access, validation and the ticket lifecycle through the HTTP API."""

import pytest


def _create(client, **overrides):
    body = {
        "book_id": "BK016",
        "subject": "Royalty question",
        "description": "The Nagpur Notebooks has sold 34 copies but I have never been paid. Why?",
    } | overrides
    return client.post("/api/tickets", json=body)


# --- Auth ---------------------------------------------------------------------------------


def test_login_rejects_wrong_password_with_generic_message(anon):
    response = anon.post("/api/auth/login", json={"email": "admin@bookleaf.com", "password": "nope"})
    assert response.status_code == 401
    assert response.json() == {"error": {"code": "unauthorized", "message": "Invalid email or password"}}


def test_login_is_case_insensitive_on_email_and_me_returns_user(anon):
    response = anon.post("/api/auth/login", json={"email": "Priya.Sharma@Email.com", "password": "author123"})
    assert response.status_code == 200
    assert anon.get("/api/auth/me").json()["author_id"] == "AUTH001"


def test_bearer_token_works_for_api_clients(anon):
    token = anon.post("/api/auth/login", json={"email": "admin@bookleaf.com", "password": "admin123"}).json()[
        "access_token"
    ]
    anon.cookies.clear()
    assert anon.get("/api/admin/tickets/stats", headers={"Authorization": f"Bearer {token}"}).status_code == 200


@pytest.mark.parametrize("path", ["/api/books", "/api/tickets", "/api/admin/tickets", "/api/royalties/summary"])
def test_protected_routes_require_login(anon, path):
    response = anon.get(path)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


# --- Role-based access ------------------------------------------------------------------------


def test_author_sees_only_own_books(priya):
    books = priya.get("/api/books").json()
    assert {b["id"] for b in books} == {"BK001", "BK002"}
    assert priya.get("/api/books/BK003").status_code == 404  # someone else's: not found, not forbidden


def test_authors_cannot_use_admin_endpoints(priya):
    assert priya.get("/api/admin/tickets").status_code == 403
    assert priya.patch("/api/admin/tickets/1", json={"status": "closed"}).status_code == 403


def test_admins_use_admin_endpoints_not_author_ones(admin):
    assert admin.get("/api/tickets").status_code == 403
    assert _create(admin).status_code == 403


def test_author_cannot_read_or_reply_to_another_authors_ticket(priya):
    # Ticket 1 is a seeded ticket from Ananya.
    assert priya.get("/api/tickets/1").status_code == 404
    assert priya.post("/api/tickets/1/messages", json={"body": "hi"}).status_code == 404


# --- Validation -------------------------------------------------------------------------------


def test_create_ticket_validates_fields(kavita):
    response = _create(kavita, subject="Hi", description="short")
    assert response.status_code == 422
    fields = {d["field"] for d in response.json()["error"]["details"]}
    assert fields == {"subject", "description"}


def test_create_ticket_rejects_another_authors_book(kavita):
    response = _create(kavita, book_id="BK001")
    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "book_id"


def test_create_ticket_rejects_unknown_fields(kavita):
    assert _create(kavita, priority="critical").status_code == 422  # authors can't set priority


def test_assigning_to_a_non_admin_is_rejected(admin):
    response = admin.patch("/api/admin/tickets/1", json={"assigned_admin_id": 3})
    assert response.status_code == 422


# --- Lifecycle ---------------------------------------------------------------------------------


def test_general_ticket_without_book(kavita):
    response = _create(kavita, book_id=None, subject="Changing my bank account")
    assert response.status_code == 201
    assert response.json()["book"] is None


def test_full_ticket_lifecycle(kavita, admin, fake_llm):
    fake_llm.responses = ['{"category": "royalty_payments", "priority": "medium", "reasoning": "Below threshold."}']
    created = _create(kavita).json()
    ticket_id = created["id"]
    assert created["status"] == "open"

    # Triage ran in the background after the response.
    detail = admin.get(f"/api/admin/tickets/{ticket_id}").json()
    assert (detail["category"], detail["priority"], detail["ai_status"]) == ("royalty_payments", "medium", "completed")
    assert detail["category_source"] == "ai"

    admin.post(f"/api/admin/tickets/{ticket_id}/notes", json={"body": "Explain rollover"})
    reply = admin.post(
        f"/api/admin/tickets/{ticket_id}/messages",
        json={"body": "Hi Kavita, here's how it works...", "used_ai_draft": True},
    ).json()
    assert reply["status"] == "in_progress"  # replying to an open ticket moves it on
    assert reply["assigned_admin"]["name"] == "Aarav Mehta"  # first responder owns it
    assert reply["awaiting_team_reply"] is False

    # The author sees the reply but nothing internal.
    author_view = kavita.get(f"/api/tickets/{ticket_id}").json()
    assert [m["body"] for m in author_view["messages"]] == ["Hi Kavita, here's how it works..."]
    for hidden in ("internal_notes", "priority", "ai_reasoning", "assigned_admin"):
        assert hidden not in author_view

    admin.patch(f"/api/admin/tickets/{ticket_id}", json={"status": "resolved"})
    followup = kavita.post(f"/api/tickets/{ticket_id}/messages", json={"body": "One more question"}).json()
    assert followup["status"] == "open"  # an author follow-up reopens a resolved ticket
    assert followup["awaiting_team_reply"] is True

    admin.patch(f"/api/admin/tickets/{ticket_id}", json={"status": "closed"})
    assert kavita.post(f"/api/tickets/{ticket_id}/messages", json={"body": "Hello?"}).status_code == 409


def test_admin_override_is_marked_and_kept(admin):
    response = admin.patch("/api/admin/tickets/6", json={"category": "isbn_metadata", "priority": "high"}).json()
    assert response["category_source"] == response["priority_source"] == "admin"


def test_queue_puts_urgent_unresolved_first(admin):
    admin.patch("/api/admin/tickets/6", json={"priority": "critical"})
    admin.patch("/api/admin/tickets/3", json={"priority": "low"})
    items = admin.get("/api/admin/tickets").json()["items"]
    assert items[0]["id"] == 6
    assert items[-1]["status"] == "resolved"


def test_queue_filters(admin):
    admin.patch("/api/admin/tickets/2", json={"priority": "high", "category": "isbn_metadata"})
    page = admin.get("/api/admin/tickets", params={"category": "isbn_metadata", "status": "in_progress"}).json()
    assert [t["id"] for t in page["items"]] == [2]
    assert admin.get("/api/admin/tickets", params={"q": "ISBN"}).json()["total"] >= 1
    assert admin.get("/api/admin/tickets", params={"assigned": "unassigned"}).json()["total"] == 4


def test_unknown_api_route_returns_json_404(anon):
    response = anon.get("/api/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
