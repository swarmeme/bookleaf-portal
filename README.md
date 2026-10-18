# BookLeaf Author Support & Communication Portal

A support portal for BookLeaf Publishing with two interfaces:

- **Author portal:** authors log in, see their books with sales and royalty figures, raise support tickets, and follow replies in real time.
- **Admin portal:** the BookLeaf ops team works a prioritised ticket queue. AI classifies and prioritises every ticket and drafts replies from the BookLeaf knowledge base and the author's own account data. Admins review and edit drafts before sending, override triage, assign tickets and keep internal notes.

**Stack:** FastAPI (Python) · SQLite + SQLAlchemy 2 + Alembic · Google Gemini · React 18 + Vite + TypeScript · TanStack Query · Server-Sent Events.

---

## Contents

1. [Quick start (local)](#1-quick-start-local)
2. [Demo accounts](#2-demo-accounts)
3. [Architecture](#3-architecture)
4. [AI integration](#4-ai-integration)
5. [API reference](#5-api-reference)
6. [Testing](#6-testing)

---

## 1. Quick start (local)

### Prerequisites

| Tool | Version | Check |
|---|---|---|
| Python | 3.11 or newer (developed on 3.14) | `python3 --version` |
| Node.js | 18 or newer (developed on 20) | `node --version` |
| A Gemini API key | Optional; free at [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | |

Without a Gemini key the app still runs fully in **fallback mode**: keyword-based triage, and admins write replies by hand.

### Step 1: Backend

```bash
cd backend

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env                 # Windows: copy .env.example .env
# Edit .env: set JWT_SECRET to a long random string, and GEMINI_API_KEY if you have one.
#   python -c "import secrets; print(secrets.token_urlsafe(48))"

# Run the API on http://localhost:8000
uvicorn app.main:app --reload --port 8000 --timeout-graceful-shutdown 1
```

On first start the app applies the database migrations (Alembic), creates `backend/bookleaf.db`, and seeds it with the provided sample data (10 authors, 18 books), two admin accounts and six demo tickets. The demo tickets are triaged by the AI (or the keyword fallback) in the background a few seconds after startup.

`--timeout-graceful-shutdown 1` stops `--reload` from waiting on open real-time (SSE) connections when you edit code.

Interactive API docs (Swagger): **http://localhost:8000/docs**

### Step 2: Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. Vite proxies `/api` to the backend on port 8000, so the browser sees a single origin. Cookies and SSE work with no CORS setup.

### Alternative: run everything from one server

```bash
cd frontend && npm install && npm run build      # outputs frontend/dist
cd ../backend && uvicorn app.main:app --port 8000
```

When `frontend/dist` exists, FastAPI serves the built app too, so everything is on **http://localhost:8000**.

### Useful commands

```bash
# (in backend/, with the venv active)
python -m app.seed.seed --reset      # wipe the database and reseed from scratch
alembic upgrade head                 # apply migrations manually (startup also does this)
alembic revision --autogenerate -m "describe change"   # after changing a model
pip install -r requirements-dev.txt && pytest           # run the test suite
```

---

## 2. Demo accounts

| Role | Email | Password | Good for testing |
|---|---|---|---|
| Admin | `admin@bookleaf.com` | `admin123` | Ticket queue, AI drafts, triage overrides |
| Admin | `ops@bookleaf.com` | `admin123` | A second team member, for assignment |
| Author | `priya.sharma@email.com` | `author123` | Two published books, one with pending royalty |
| Author | `kavita.deshmukh@email.com` | `author123` | One book **in production**, one with **₹850 pending (below the ₹1,000 payout threshold)** |
| Author | `ananya.reddy@email.com` | `author123` | Published 2024, **never paid** (flagged as possibly overdue) |
| Author | `sneha.kulkarni@email.com` | `author123` | Three books including one in production |

All 10 authors in the dataset can log in with their dataset email and `author123`. The login page has one-click buttons for the main demo accounts.

**Seeing real-time updates:** open the admin queue in one browser and an author account in a private window. Submit a ticket as the author and it appears in the queue within a second. Reply as the admin and the reply appears on the author's ticket page without a refresh.

---

## 3. Architecture

```
 Browser (React + Vite)                         FastAPI (Python)
┌────────────────────────┐   REST /api/*     ┌──────────────────────────────────────────┐
│ Author portal          │ ────────────────▶ │ api/routes   thin HTTP layer + auth/RBAC  │
│ Admin portal           │                   │      │                                    │
│ TanStack Query cache ◀─┼── SSE /api/events │ services     ticket workflow, royalty     │
└────────────────────────┘   (invalidate)    │      │       rules, event broker, triage  │
                                             │ ai           Gemini client, prompts,      │
                                             │      │       knowledge base, fallback     │
                                             │ models       SQLAlchemy ─▶ SQLite         │
                                             └──────────────────────────────────────────┘
```

### Backend layout

```
backend/
  app/
    main.py             app setup, router registration, serves frontend/dist if built
    core/               config (env vars), database, security (JWT, bcrypt), error handling
    models/             SQLAlchemy models: User, Author, Book, Ticket, TicketMessage, InternalNote
    schemas/            Pydantic request/response models (separate author vs admin views)
    api/deps.py         authentication + role guards used by every protected route
    api/routes/         auth, books, royalties, tickets (author), admin, events (SSE)
    services/
      tickets.py        ticket workflow and queue queries, including access rules
      royalty.py        payout rules from the knowledge base, as code
      triage.py         background AI triage + recovery of pending tickets on startup
      events.py         in-process pub/sub for real-time updates
    ai/
      client.py         Gemini wrapper: timeout, retries, circuit breaker
      knowledge_base.py BookLeaf knowledge base, split by category
      context.py        turns DB records into compact factual prompt context
      prompts.py        prompt templates
      classifier.py     category + priority (AI, with keyword fallback)
      fallback.py       keyword triage rules
      drafter.py        reply drafts with caching
    seed/               sample dataset + seeding
  migrations/           Alembic migrations
  tests/                pytest suite (AI is faked; no network needed)
```

### Key decisions

**Layering: routes → services → models, with AI as its own package.** Route handlers only parse input and pick a response model. Business rules live in `services/`, such as "a reply from the team moves an open ticket to In Progress", "an author follow-up reopens a resolved ticket" and "the first responder gets assigned". Everything provider-specific is in `ai/client.py`. Switching from Gemini to another LLM means writing one class with the same `generate()` signature.

**Separate author and admin endpoints and response models.** Authors use `/api/tickets/*` and admins use `/api/admin/tickets/*`. The author response models have no fields for priority, AI reasoning, assignee or internal notes, so those can't leak through a serialisation mistake. Internal notes also live in their own table. Another author's ticket or book returns 404, not 403, so IDs can't be probed.

**Authentication: JWT in an httpOnly, SameSite=Lax cookie.** JavaScript can't read the token, which protects it from XSS. SameSite blocks cross-site form posts, and cookies also work with `EventSource`, which can't send headers. The login response also returns the token, and `Authorization: Bearer` is accepted, so the API works from curl and Postman. Passwords are hashed with bcrypt.

**Errors: one JSON shape for every failure**, `{"error": {"code", "message", "details?"}}`, covering validation (422 with per-field messages), auth (401/403), not found (404), conflicts (409, e.g. replying to a closed ticket) and unexpected errors (500 with a safe message, full trace in the server log).

**Ticket creation never waits on the AI.** The ticket is saved and returned immediately, and triage runs as a background task. If the server restarts before triage runs, the ticket stays `ai_status = pending` and is picked up on the next startup.

**Triage fields record their source.** `category_source` / `priority_source` is `ai`, `fallback` (keyword rules) or `admin`. The queue shows this, so the team knows which values to double-check. A later AI re-run never overwrites an admin override unless the admin explicitly asks for re-triage.

**Real-time updates: Server-Sent Events, not WebSockets or polling.** Updates only flow server → browser, so SSE is enough and runs over plain HTTP. The browser reconnects automatically, and it needs no extra infrastructure. Events are tiny ("ticket 7 changed"); the client refetches through the normal REST endpoints, so permission checks stay in one place. Authors only receive events for their own tickets, and never `ticket.note` events. After a reconnect the client refetches everything, since events sent while it was disconnected are lost.

**Database: SQLite + Alembic.** No setup is needed to run locally. The schema is portable: enums are stored as strings and all timestamps are timezone-aware UTC. Moving to Postgres means changing `DATABASE_URL`. Migrations run automatically on startup. Money is stored as whole rupees, matching the source data.

**Royalty rules as code (`services/royalty.py`).** The knowledge base's payout policy is implemented as tested functions: quarterly calculation, a 45-day payout window and the ₹1,000 minimum. They compute the next payout date and a per-book payout status (`paid_up`, `below_threshold`, `scheduled`, `possibly_overdue`, `not_earning`). The author dashboard shows these, and they are passed to the AI as facts, so drafts quote real dates instead of guessing.

**Demo date.** The dataset's payout dates are from 2025, so `AS_OF_DATE=2026-01-20` pins "today" for royalty calculations. Without it, almost every book would look overdue. Ticket timestamps use the real clock.

### Frontend

- **React + Vite + TypeScript**, with React Router for the two portals. Routes are guarded by role; the API enforces access as well.
- **TanStack Query** for server state. Each SSE event invalidates the affected queries (queue, stats, ticket), so every open view refreshes itself.
- Queue filters are kept in the URL, so a filtered view survives navigation and can be shared.
- No UI library. The CSS is a small set of variables plus components (~350 lines), so there are fewer dependencies to explain or maintain.

Product details worth noting:
- Authors see their royalty position in plain language ("Your ₹850 rolls over until it reaches ₹1,000") and a stage tracker for books in production, instead of a row of zeros.
- The queue sorts unresolved tickets by urgency (critical, high, untriaged, medium, low), then oldest first. Unresolved tickets older than 48 hours have their age highlighted in red, critical tickets get a red edge, and tickets where the author is waiting on BookLeaf are marked "needs reply". Clicking a summary tile (Need a reply, Critical open, Unassigned) filters the queue.
- Admins get "Send" and "Send & resolve". The first reply assigns the ticket to whoever sent it.
- A follow-up from the author reopens a resolved ticket. Closed tickets point the author to a new ticket.

---

## 4. AI integration

### What the AI does

| Feature | When | Model (default) | Output |
|---|---|---|---|
| **Triage** | In the background after each new ticket | `gemini-3.5-flash-lite` | JSON constrained by a schema: category, priority, one-sentence reasoning for the admin |
| **Reply draft** | When an admin opens a ticket that is waiting on the team (or on request) | `gemini-3.8-flash` | Plain-text reply in BookLeaf's voice, editable before sending |

### Model choice: Gemini

- **Cost and free tier.** Flash-Lite is one of the cheapest capable models available, and Flash is a low-cost model with good writing. Both are on Google AI Studio's free tier, so reviewers can run the full AI path without a paid account.
- **Native structured output.** `response_schema` constrains triage to valid enum values, so the code never parses free text for a category.
- **Two tiers for two jobs.** Triage is short pattern-matching, so it uses the cheapest model. Drafting is customer-facing writing, so it uses the stronger one.
- **Thinking is kept low** (`GEMINI_THINKING_LEVEL=LOW`). Gemini 3+ models think before answering by default. Thinking adds latency, and its tokens count against the output limit: in testing, `gemini-3.8-flash` at its default level returned a reply cut off mid-sentence. Both tasks are well specified, so `LOW` loses nothing. (`MINIMAL` isn't supported by `gemini-3.8-flash`.)
- The older `gemini-2.5-*` models are no longer available to new API keys, so the defaults are the current Flash-Lite and Flash models. Both are configurable in `.env`.

### Prompt strategy (`ai/prompts.py`)

Each prompt has two parts:

1. **A system instruction** with the role, the rules and (for drafts) BookLeaf's tone guidelines and company overview, copied from the knowledge base. It's the same for every call.
2. **User content** with only what this ticket needs, in tagged blocks: `<policy>`, `<reference_examples>`, `<account_facts>`, `<ticket>` and `<conversation>`.

How this targets "sounds like BookLeaf, not generic AI":

- **Grounded in real account facts.** `ai/context.py` turns the database into short factual lines: the author's first name, the book's status, copies sold, royalty earned/paid/pending, last payout date, the computed next payout date, the payout status and where the book is listed. The rules say: *use only the policy and facts provided, never invent amounts, dates or policies; if you need information you don't have, say the team will check it and give a timeline.*
- **Tells the model when BookLeaf is at fault.** When the royalty rules flag a payout as `POSSIBLY OVERDUE`, the facts say so explicitly. The rules tell the model to own it, apologise and escalate with a 48-hour timeline, as the tone guide requires.
- **Calibrated with the knowledge base's own examples.** The sample query and response guidance for the ticket's category is included as *how to respond*, not text to copy.
- **Fixed format.** Plain text, greets the author by first name, 100–220 words, ends with a clear next step, and always signs off as "BookLeaf Author Support". Drafts read the same whichever admin sends them.
- **Priority rubric based on impact.** The triage prompt defines each level with concrete examples (ISBN errors are always at least *high*, per policy). It tells the model that angry wording alone doesn't raise priority, and it passes the royalty facts, so "no royalty yet" with ₹850 pending (below the threshold) ranks lower than with ₹5,000 overdue.
- **Prompt-injection guard.** Author text is wrapped in `<ticket>` / `<conversation>` tags, and the system instruction says to treat it as data, never as instructions.

### Graceful degradation

| Failure | What happens |
|---|---|
| No API key | App runs in fallback mode. Triage uses keyword rules (`ai/fallback.py`) with `ai_status = disabled`. The draft panel says AI drafting isn't configured and the admin writes the reply. |
| Rate limit (429) or server error (5xx) | Retried with exponential backoff and jitter (1s, 2s; configurable), then falls back. Seen in testing on the free tier: the draft panel showed "AI rate limit reached" and the admin could still reply by hand. |
| Bad request / invalid key (4xx) | Not retried (retrying can't help); falls back immediately. |
| Timeout / network error | 20s timeout, retried, then falls back. |
| Repeated failures | **Circuit breaker:** after 3 consecutive failures, AI calls are skipped for 60s, so an outage doesn't add a 20s+ wait to every ticket. |
| Malformed AI output | The triage JSON is validated with Pydantic. Invalid output is treated as a failure, so keyword rules apply. |
| Empty / blocked response | Treated as a failure. |

In every case the ticket is still created, the admin can still work it, and the queue labels what happened ("Rules" tag, "Re-run AI triage" button). The draft endpoint returns **200** with `status: "unavailable"` and a message, not an error, because the admin's workflow carries on. Failures are logged in the server log.

### Cost management

The app doesn't meter tokens; costs are tracked at the AI provider's billing level. The design keeps each call small:

1. **Only the relevant slice of the knowledge base is sent.** Each draft gets its category's policy and examples plus the tone guidelines, a fraction of the full knowledge base. General inquiries get a compact digest of every policy (`ai/knowledge_base.py`).
2. **Drafts are cached on the ticket.** Reopening a ticket, or several admins viewing it, costs nothing. The cache is cleared only when the draft would be wrong: a new message in the thread, or a category change, which changes which policy applies.
3. **Drafts are generated only when needed.** A draft is generated automatically only when the author is waiting on the team. Otherwise the admin clicks "Draft with AI".
4. **History and input are bounded.** Only the last 4 thread messages are sent, each truncated to 800 characters, with a note when earlier messages are omitted. The triage description is capped at 1,500 characters (triage only needs the gist), the draft description at 4,000.
5. **Facts are compact.** Only the book the ticket is about is included, as a few lines of text, never the author's whole record. Triage gets a single summary line.
6. **The cheap model triages, temperature is 0, and thinking is kept low.** Output length is capped.
7. **Draft usefulness is recorded.** Each sent reply stores `used_ai_draft`, so the team can see how often replies start from an AI draft. The admin thread labels those replies "AI-assisted".

### API key security

- The key is read only from the environment (`backend/.env`, which is gitignored) via `pydantic-settings`. It's never hardcoded, logged or returned by any endpoint.
- All AI calls happen on the server. The frontend never talks to Gemini and never sees the key; it only gets `ai_enabled: true/false` from `/api/health`.

---

## 5. API reference

Full interactive documentation with request/response schemas: **http://localhost:8000/docs** (Swagger UI) or `/openapi.json`.

All endpoints are under `/api`. Every endpoint except `POST /auth/login` and `GET /health` requires authentication. Errors always look like:

```json
{ "error": { "code": "validation_error", "message": "Some fields are invalid",
             "details": [{ "field": "subject", "message": "String should have at least 5 characters" }] } }
```

### Auth

| Method | Path | Who | Description |
|---|---|---|---|
| POST | `/auth/login` | public | `{email, password}` → sets the httpOnly cookie; also returns `{user, access_token}` |
| POST | `/auth/logout` | any | Clears the cookie (204) |
| GET | `/auth/me` | any | The logged-in user |

### Author

| Method | Path | Description |
|---|---|---|
| GET | `/books` | Own books (admins: all books, `?author_id=` filter) |
| GET | `/books/{book_id}` | One book (another author's book → 404) |
| GET | `/royalties/summary` | Totals, payout threshold, next payout date, per-book payout status |
| GET | `/tickets` | Own tickets, most recently updated first. `?status=` (repeatable), `page`, `page_size` |
| POST | `/tickets` | Raise a ticket: `{book_id?, subject (5–200), description (20–5000), attachment_name?}` → 201. Triage runs in the background |
| GET | `/tickets/{id}` | Ticket with the author-visible thread |
| POST | `/tickets/{id}/messages` | Follow-up `{body}`. Reopens a resolved ticket; 409 if closed |

### Admin

| Method | Path | Description |
|---|---|---|
| GET | `/admin/tickets` | Queue. Filters: `status` (repeatable), `category`, `priority`, `assigned=me\|unassigned`, `awaiting_reply`, `book_id`, `created_from`, `created_to` (YYYY-MM-DD), `q` (search). `sort=urgency\|newest\|oldest\|updated`. Paginated |
| GET | `/admin/tickets/stats` | Counts: by status, unassigned, awaiting reply, critical open, pending triage |
| GET | `/admin/tickets/{id}` | Full ticket: thread, internal notes, AI reasoning, author profile, book details |
| PATCH | `/admin/tickets/{id}` | Any of `{status, category, priority, assigned_admin_id}`. Category/priority changes are marked `source: admin` |
| POST | `/admin/tickets/{id}/messages` | Reply `{body, used_ai_draft?, status?}`. Optional `status` sends and resolves in one step |
| POST | `/admin/tickets/{id}/notes` | Internal note `{body}` (never visible to the author) |
| POST | `/admin/tickets/{id}/draft` | AI draft. Returns the cached draft unless `?regenerate=true`. `{status: generated\|cached\|unavailable, draft, generated_at, message}` |
| POST | `/admin/tickets/{id}/triage` | Re-run AI triage (202). Clears manual overrides |
| GET | `/admin/team` | Admin users, for assignment |

### Real-time and meta

| Method | Path | Description |
|---|---|---|
| GET | `/events` | SSE stream: `ticket.created`, `ticket.updated`, `ticket.message`, `ticket.note` (admins only). Data: `{type, ticket_id, author_id}` |
| GET | `/health` | `{status, ai_enabled}` |

### Example (curl)

```bash
# Log in and keep the cookie
curl -c cookies.txt -X POST localhost:8000/api/auth/login \
  -H 'content-type: application/json' -d '{"email":"priya.sharma@email.com","password":"author123"}'

# Raise a ticket
curl -b cookies.txt -X POST localhost:8000/api/tickets -H 'content-type: application/json' \
  -d '{"book_id":"BK001","subject":"Royalty seems low","description":"I sold 342 copies but the payout feels low. How is it calculated?"}'

# Watch live events
curl -N -b cookies.txt localhost:8000/api/events
```

---

## 6. Testing

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

The 50 tests run in a few seconds. Each test gets a fresh copy of a migrated, seeded SQLite database. The LLM is replaced with a fake that records prompts, so tests need no network and no API key. They cover:

- **Auth and access control:** cookie and Bearer auth, 401s on every protected route, authors can't reach other authors' books/tickets or admin endpoints, admins can't use author endpoints.
- **Validation:** field errors, unknown fields rejected (an author can't set `priority`), books must belong to the author, assignees must be admins.
- **Ticket lifecycle:** create → AI triage → note → reply (auto In Progress and auto-assign) → resolve → author follow-up reopens → closed rejects replies. Author views never contain internal fields.
- **AI:** triage applied from the AI; fallback when the AI is down or returns invalid JSON; prompts are size-capped and wrap ticket text as data; drafts are cached and invalidated by new messages; draft prompts contain only the relevant policy plus real figures; books in production get no royalty figures; "unavailable" is a 200.
- **Gemini client:** retries 429s, doesn't retry 400s, and the circuit breaker stops calls after repeated failures.
- **Royalty rules:** next payout date across quarter boundaries, and payout status for real sample-data authors (paid up, below threshold, possibly overdue, in production).
- **Real-time:** the event broker only delivers events a subscriber is allowed to see.

