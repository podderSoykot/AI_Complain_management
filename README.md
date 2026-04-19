# AI-Powered Customer Complaint & Support System

A scalable architecture for a multi-tenant, AI-driven customer support platform where users submit complaints (tickets), and the system automatically:

- Understands the issue using AI
- Prioritizes it intelligently
- Routes it to the correct team
- Helps agents resolve faster using AI suggestions and knowledge retrieval
- Tracks everything in a scalable workflow system

## Assignment handover

Use this section to onboard the next maintainer or to submit the project.

### Repository map

| Area | Location |
|------|----------|
| FastAPI app | `main.py`, `app/` |
| Frontend (Vite) | `Frontend/` — build output `Frontend/dist/` |
| Docker (API + Postgres) | `Dockerfile`, `docker-compose.yml` |
| Env loading | `app/core/config.py` (reads repo root `.env`) |

### End-user documentation

| Document | Audience |
|----------|----------|
| [User guide](./docs/USER_GUIDE.md) | Customers (submit tickets, AI chat, profile) |
| [Admin & employee guide](./docs/ADMIN_AND_EMPLOYEE_GUIDE.md) | Admins and support staff (agents / supervisors) |

### AI / LLM configuration (required for AI features)

If you see **“AI assistant isn’t configured”** or **`LLM_MODE=api requires OPENAI_API_KEY`**, the backend cannot call an LLM until you set the variables below in **`.env`** (local) or in your host’s environment (Render, Docker, etc.).

| Setup | Set these |
|-------|-----------|
| **Local model** (Ollama, LM Studio, or any OpenAI-compatible server) | `LLM_MODE=local`, `LOCAL_LLM_BASE_URL` (e.g. `http://127.0.0.1:11434/v1` for Ollama), `LOCAL_LLM_MODEL` (must match an available model). Optional: `LOCAL_LLM_API_KEY`, `LOCAL_LLM_TIMEOUT_SECONDS`. |
| **Cloud API** (OpenAI or compatible) | `LLM_MODE=api`, `OPENAI_API_KEY`. Optional: `OPENAI_API_BASE` (default `https://api.openai.com/v1`), `AI_MODEL` (e.g. `gpt-4o-mini`), `OPENAI_TIMEOUT_SECONDS`. |

**Hosted API note:** On Render (or similar), `LLM_MODE=local` with `127.0.0.1` only works if a compatible LLM process runs **in the same container** or you point `LOCAL_LLM_BASE_URL` at a reachable URL. For most cloud deployments, use **`LLM_MODE=api`** and a valid **`OPENAI_API_KEY`**.

Validation logic: `app/features/llm/config_check.py`.

### Deployment checklist (typical)

1. **Backend:** Set `DATABASE_URL`, `JWT_SECRET_KEY`, `ADMIN_EMAIL` / `ADMIN_PASSWORD`, and LLM variables above. CORS in `main.py` must include your frontend origin (e.g. Vercel URL).
2. **Frontend (Vercel):** Build command `npm run build` from `Frontend/`, output `dist`. Optional env: `VITE_API_ORIGIN` (public API base URL without trailing slash).
3. **Docker:** `docker compose up --build` — see `docker-compose.yml`; optional `.env` for overrides.

### Health

- `GET /api/v1/health`

---

## Architecture Docs

- Scalable architecture: [`docs/SCALABLE_SYSTEM_DESIGN.md`](./docs/SCALABLE_SYSTEM_DESIGN.md)
- System design diagrams: [`docs/SYSTEM_DESIGN_DIAGRAM.md`](./docs/SYSTEM_DESIGN_DIAGRAM.md)
- Direct PNG diagram: [`docs/system-design-diagram.png`](./docs/system-design-diagram.png)
- Ticket lifecycle PNG: [`docs/ticket-lifecycle.png`](./docs/ticket-lifecycle.png)

## FastAPI Implementation

Implemented backend (production-style starter) with:

- FastAPI app in `main.py`
- Async SQLAlchemy: engine/session in `app/database/session.py`, models on `Base` in `app/database/base.py`
- Decorator + middleware latency measurement in `app/core/perf.py`
- Ticket domain logic and enrichment in `app/features/tickets/service.py` (explicit-column style queries where used)
- Advanced Python concurrency in ticket enrichment:
  - `ThreadPoolExecutor` for parallel sentiment scoring
  - `ProcessPoolExecutor` for CPU-bound classification and priority
  - `asyncio.gather` for concurrent enrichment
- OpenAI-compatible chat completions in `app/features/llm/client.py` (local Ollama or remote API)

### Run

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Optional UI: static/Vite app under `Frontend/` (e.g. `npm install` then `npm run dev` — CORS allows `localhost:5173`).

### Configuration (`.env`)

Copy values into `.env` at the repo root (loaded from `app/core/config.py`).

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` / `database_url` | Postgres (asyncpg) or SQLite (`sqlite+aiosqlite:///...`) |
| `JWT_SECRET_KEY` | Sign JWTs (change in production) |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | Bootstrap admin user on startup |
| `LLM_MODE` | `local` = Ollama/LM Studio OpenAI-compatible endpoint; `api` = remote key |
| `LOCAL_LLM_BASE_URL` | Default `http://127.0.0.1:11434/v1` when `LLM_MODE=local` |
| `LOCAL_LLM_MODEL` | e.g. `llama3.2:3b` (must match `ollama list`) |
| `LOCAL_LLM_TIMEOUT_SECONDS` | HTTP timeout for local LLM (default `600`; first inference can be slow) |
| `OPENAI_API_KEY` | Required when `LLM_MODE=api` |
| `OPENAI_API_BASE`, `AI_MODEL` | Remote base URL and model when using API mode |
| `OPENAI_TIMEOUT_SECONDS` | HTTP timeout for API mode (default `120`) |

If the UI or logs show **`LLM_MODE=api requires OPENAI_API_KEY`** or **AI assistant isn’t configured**, see **Assignment handover → AI / LLM configuration** above.

`tenant_id` is auto-generated during user creation from the email domain.

### Implemented features (detailed)

The following describes **what this repository actually implements** today: backend (FastAPI), enrichment logic, admin/employee/customer flows, LLM integration, and the Vite frontend.

---

#### 1. Platform, security, and observability

- **FastAPI** application (`main.py`) with modular routers under `app/features/`.
- **Async SQLAlchemy** with `AsyncSession` and connection pooling (`app/database/session.py`); supports **SQLite** (default) and **PostgreSQL** via `asyncpg` when `DATABASE_URL` uses the async URL form.
- **JWT authentication**: access tokens embed subject (email) and role; signed with `JWT_SECRET_KEY` (`app/core/security.py`). Token lifetime is controlled by `access_token_expire_minutes` in settings.
- **HTTP Bearer** dependency (`get_current_user`) protects routes; separate guards for **admin-only** and **support/supervisor-only** actions (`app/features/users/deps.py`).
- **CORS** middleware allows configured browser origins (local dev ports and production frontend URLs — adjust `main.py` for new deploy hosts).
- **Request timing**: middleware adds a processing-time header (`app/core/perf.py`); `/api/v1/health` is wrapped for basic latency visibility.
- **Startup lifecycle**: on boot, ORM creates tables, applies lightweight compatibility `ALTER`s where needed, seeds **agent** rows if empty, and ensures an **admin** user exists when `ADMIN_EMAIL` / `ADMIN_PASSWORD` are set (`main.py`).

---

#### 2. Users, tenants, and authentication

- **Roles** supported in the data model and JWT: `customer`, `support_agent`, `supervisor`, `admin`.
- **Multi-tenant key**: `tenant_id` is **derived from the email domain** (normalized, e.g. `user@acme.com` → a stable tenant string). This groups users for listing and isolation-style queries.
- **Registration** (`POST /api/v1/users`): creates a user with hashed password (`passlib` + bcrypt), rejects duplicate emails.
- **Login variants**:
  - **General** (`POST /api/v1/users/login`): any active user; returns token + role.
  - **Admin** (`POST /api/v1/users/login/admin`): same credential check but **403** unless `role == admin` (intended for admin UI flows).
  - **Employee** (`POST /api/v1/users/login/employee`): **403** unless role is `support_agent` or `supervisor`.
- **User lookup**: `GET /api/v1/users/{user_id}` returns public profile fields; `GET /api/v1/users?tenant_id=...` lists users in a tenant with optional `role` filter (used for directory-style features).
- **Bootstrap admin**: if `ADMIN_EMAIL` and `ADMIN_PASSWORD` are configured, startup ensures that account exists (for first-run and demos).

---

#### 3. Tickets: data model and workflow

Each **ticket** stores: title, long description, **category**, **priority**, **sentiment**, **status**, optional **assignee** (`assignee_id`), and **reporter** (`reporter_id`). Status values used in code include: `open`, `assigned`, `in_review`, `in_progress`, `resolved`, `closed` (exact transitions depend on assignee and admin actions).

- **Customers** may only see tickets they **reported** (reporter match). **Admins** and **support/supervisor** users can see tickets broadly for operations.
- **Closing policy**: admin **close** is only allowed for tickets already in a **resolved** state, and the ticket is expected to have been **resolved by an assigned employee** first (enforced in `close_ticket_by_admin`).

---

#### 4. Ticket creation, attachments, and automatic enrichment (non-LLM)

- **Create ticket** (`POST /api/v1/tickets`): **multipart/form-data** with `title` (3–160 chars), `description` (10–4000 chars), optional **multiple file uploads**. Requires authenticated user (typically **customer**). Enforces max **file count** and **per-file size** from environment (`TICKET_MAX_FILES`, `TICKET_MAX_UPLOAD_BYTES`).
- **Allowed file types** are validated by extension and MIME heuristics (e.g. PDF, common images, office types — see `ALLOWED_ATTACHMENT_SUFFIXES` in `service.py`). Files are stored under `TICKET_UPLOAD_DIR` with a **UUID stored name**; metadata is saved in `ticket_attachments`.
- **Enrichment pipeline** (`create_ticket_enriched`): after insert, title + description text is analyzed **without** calling an LLM:
  - **Category** (`classify_text`): keyword/phrase rules in **English and Bangla** — buckets such as **billing**, **account**, **technical**, else **complaint**.
  - **Sentiment** (`sentiment_score`): heuristic label used for triage.
  - **Priority** (`priority_score`): combines text signals and sentiment into levels such as **medium**, **high**, **critical**.
- **Concurrency**: classification and sentiment run in **process/thread pools** (`ProcessPoolExecutor` / `ThreadPoolExecutor`) and are awaited together with `asyncio` to keep the API responsive.

---

#### 5. Ticket conversations and collaboration

- **Threaded messages** (`ticket_conversations`): participants with ticket access can **post** messages with a **message_type** (e.g. notes vs other types supported by the schema) and **list** history (ordered, limit up to 1000). Messages record sender user id and **sender role** for auditing.
- **AI “sender”** uses a reserved id constant in AI support code when persisting automated lines into the thread (`ai_support.py`).

---

#### 6. Attachments: list and download

- Ticket payloads include **public attachment metadata** (original name, MIME, size, timestamps) without exposing disk paths.
- **Download** (`GET .../attachments/{attachment_id}/download`) checks **authorization** (`user_can_view_ticket_files`), resolves the stored file, and streams it with appropriate `Content-Type` and `Content-Disposition`.

---

#### 7. Employee (agent / supervisor) features

- **List my assignments** (`GET /api/v1/tickets/assigned/me`): returns tickets assigned to the current **support_agent** or **supervisor**, newest first (limit capped).
- **Update work status** (`PATCH /api/v1/tickets/{ticket_id}/work-status`): only the **current assignee** may update; valid transitions are validated server-side (e.g. `in_review`, `in_progress`, `resolved` — errors for wrong assignee or already admin-closed tickets). This drives the operational lifecycle before admin closure.

---

#### 8. Admin: user management

- **List all users** (`GET /api/v1/admin/users`) with limit.
- **Activate/deactivate** (`PATCH .../users/{id}/status`).
- **Change role** (`PATCH .../users/{id}/role`).
- **Partial profile update** (`PATCH .../users/{id}`): name, email, role, department, active flag — with **duplicate email** protection.
- **Delete user** (`DELETE .../users/{id}`): **cannot delete own account** (guardrail).

---

#### 9. Admin: ticket operations and intelligence (non-LLM)

- **List all tickets** for oversight (`GET /api/v1/admin/tickets`).
- **Manual assign** (`POST .../assign`): assigns to a user id; validates assignee exists, is **active**, and has role **support_agent** or **supervisor**.
- **Smart assign** (`POST .../smart-assign`): recomputes NLP **category** from ticket text, scores **active employees** by **department match** vs category and by **current active ticket load**, picks a balanced assignee, then assigns. Fails clearly if no eligible employee exists.
- **Routing suggestion** (`GET .../routing-suggestion`): returns **NLP category**, **human-readable admin guidance** strings per category, a **ranked candidate list** (department fit score, active load, rationale), and a **recommended_user_id** — for UI assistance without auto-assigning.
- **Close ticket** (`PATCH .../close`): enforces **resolved-by-assignee** and status rules before `closed`.
- **Statistics** (`GET /api/v1/admin/stats`): aggregate counts — total users, total tickets, open/in-progress buckets vs resolved/closed.
- **Workload insights** (`GET /api/v1/admin/insights/workload`): per-employee **active ticket counts** (for the statuses used in load calculation), sorted for capacity planning; includes min/max summary fields.

---

#### 10. AI assistant features (LLM required)

All AI routes depend on **valid LLM configuration** (`LLM_MODE`, keys, base URLs — see Assignment handover). The client uses **OpenAI-compatible Chat Completions** (`app/features/llm/client.py`); JSON in replies may be parsed for structured actions.

- **Customer — chat on a ticket** (`POST /api/v1/tickets/{ticket_id}/ai/customer-chat`): customer-only; loads ticket + thread context; returns an assistant reply. Blocks if ticket not owned by reporter or already closed.
- **Customer — Work with agent (one-click)** (`POST /api/v1/tickets/ai/agent-run`): picks the **latest non-closed ticket reported by this customer** and runs an autonomous-style prompt (summarize, advise next steps). Returns `ticket_id` + reply.
- **Admin — copilot on a ticket** (`POST /api/v1/admin/tickets/{ticket_id}/ai/chat`): admin message + optional **apply resolution** path; may integrate with ticket resolution logic when the model returns structured signals (`ai_support.py`).
- **Admin — Work with agent (one-click)** (`POST /api/v1/admin/tickets/ai/agent-run`): targets the **newest non-closed ticket globally** for triage-style assistance.

If configuration is missing, callers see errors such as **`LLM_MODE=api requires OPENAI_API_KEY`** (see `config_check.py`).

---

#### 11. Internal “agents” table (workload / skills)

- On empty database, startup seeds named **agents** with **skills** and **current_load** (`main.py`). Helper logic can pick a **least-loaded** agent by **skill/category** (`_least_loaded_agent_for_category`) for experiments or future routing — **smart assign** in production primarily uses **User** employees and departments as described above.

---

#### 12. Frontend (Vite, multi-page)

- **SPA-style dashboard** (`index.html` + `src/main.js`): login types (**General / Admin / Employee**), sections for **Overview**, **Profile**, **Settings**, **Tickets**, and **Admin** (role-gated), **Work with agent** button when applicable, theme/settings persisted locally where implemented.
- **Additional pages** built as separate HTML entries (`vite.config.js`): `list-user.html`, `list-ticket.html`, `create-user.html`, `my-assigned-tickets.html` — each bundles its own JS module for admin or employee workflows (tables, refresh, navigation back to dashboard).
- **API base URL**: development defaults to local API; production build defaults to the deployed API origin unless overridden with **`VITE_API_ORIGIN`** (`src/admin-pages-common.js`).

---

#### 13. Docker and compose

- **Dockerfile** runs **uvicorn** serving `main:app` on port 8000.
- **docker-compose.yml** provides **PostgreSQL** with healthcheck and an **api** service with persistent volumes for DB data and ticket uploads; environment can be merged from `.env` (see compose file).

---

#### 14. API route index (quick reference)

| Area | Routes |
|------|--------|
| Health | `GET /api/v1/health` |
| Users | `POST /api/v1/users`, `POST .../login`, `.../login/admin`, `.../login/employee`, `GET /api/v1/users/{id}`, `GET /api/v1/users` |
| Tickets | `POST /api/v1/tickets`, `GET /api/v1/tickets/{id}`, `GET .../assigned/me`, `PATCH .../work-status`, attachment download, conversations GET/POST, customer AI routes |
| Admin | `GET /api/v1/admin/users`, `GET .../tickets`, assign / smart-assign / close, user PATCH/DELETE, stats, workload, routing-suggestion, admin AI routes |

### Tests

```bash
pytest -q
```

Live Ollama smoke (skipped if nothing at `127.0.0.1:11434`): `pytest test/test_work_with_agent_live_llm.py -v`.

### Project Structure

```text
app/
  core/
    config.py
    perf.py
    security.py
  database/
    base.py
    session.py
  features/
    agents/
      models.py
    llm/
      client.py
      config_check.py
      http_errors.py
      json_util.py
    tickets/
      models.py
      schemas.py
      service.py
      router.py
      ai_support.py
    users/
      models.py
      schemas.py
      service.py
      router.py
      deps.py
    admin/
      router.py
Frontend/
  (Vite / static UI)
main.py
requirements.txt
```

The sections below (**1–8** and the narrative walkthrough) describe the **target product vision** and scalability patterns. The **FastAPI Implementation** section above matches what this repository runs today (tickets, users, admin, OpenAI-compatible LLM for ticket AI and “Work with agent”).

---

## 1. User Management System (RBAC + Multi-Tenant)

### How it works

Users are divided into:

- Customer
- Support Agent
- Admin
- Supervisor (optional enterprise role)

### Features

- JWT-based authentication
- Role-Based Access Control (RBAC)
- Multi-tenant support (multiple companies in one system)

### Scalability design

- Separate `tenant_id` in every table
- Horizontal scaling per organization
- OAuth2 / SSO support for enterprise clients

---

## 2. Ticket Creation System (Omni-channel Input)

### How it works

Tickets can be created via:

- Web portal
- Email ingestion
- API integration
- Chatbot / WhatsApp (future-ready)

**Example complaint:** “Payment deducted but service not activated”

**System generates:**

- Ticket ID: `TKT-1001`
- Status: Open
- Tenant: Company_A

### Scalability

- API Gateway for all channels
- Message queue (Kafka/RabbitMQ) for ingestion
- Async ticket creation pipeline

---

## 3. AI Classification Engine (Core Intelligence Layer)

### How it works

**Pipeline:**

1. Preprocess text (cleaning, tokenization)
2. Generate embeddings (Sentence-BERT / LLM)
3. Classify into categories:
   - Billing
   - Technical
   - Account
   - Complaint

**Output example:** “Login not working” → Account Issue

### Scalability

- Microservice-based AI inference server
- Batch + real-time inference support
- Model versioning (A/B testing models)
- Cached predictions for duplicate tickets

---

## 4. AI Priority Prediction Engine

### How it works

Combines:

- Keywords (“urgent”, “not working”)
- Sentiment score
- Customer history (VIP users)
- SLA rules

**Output:** Low / Medium / High / Critical

### Scalability

- Feature store (Feast-like architecture)
- Real-time scoring API
- Rule engine + ML hybrid system

---

## 5. Sentiment Analysis System

### How it works

NLP model detects:

- Positive
- Neutral
- Negative

**Used to:**

- Escalate angry users
- Trigger fast response workflow

### Scalability

- Lightweight transformer model deployed separately
- Can be swapped with LLM API if traffic increases

---

## 6. Intelligent Ticket Routing (Auto Assignment)

### How it works

System assigns tickets based on:

- Agent skillset
- Current workload
- Ticket category
- Priority level

**Example:** Billing issue → Billing Team Agent

### Scalability

- Load-balanced assignment service
- Redis-based queue for agent workload tracking
- Dynamic routing rules engine

---

## 7. Ticket Workflow Engine (Jira-like State Machine)

### How it works

Each ticket moves through states:

`Open` → `Assigned` → `In Progress` → `Under Review` → `Resolved` → `Closed`

### Scalability

- Workflow defined in JSON/YAML
- Configurable per organization
- State machine service (decoupled from core API)

---

## 8. AI Agent Assistant (LLM + RAG System)

### How it works

Agents get AI support:

- Suggested reply drafts
- Similar past tickets
- Knowledge base retrieval

**RAG flow:**

1. Embed ticket
2. Retrieve similar issues
3. Generate response using LLM

### Scalability

- Vector DB (FAISS / Pinecone / Weaviate)
- Cached embeddings
- Distributed LLM inference layer

---

# Story: The Intelligent Customer Support System in Action

It was a busy afternoon at a digital service company that handled thousands of users every day. Everything seemed normal until a customer named **Rahim** ran into a problem.

He had just made a payment for a service, but the system didn’t activate it. Frustrated and slightly anxious, he opened the company’s support portal.

Instead of calling support or waiting endlessly on email replies, he simply wrote:

> “I paid for the service, money got deducted, but my account is still not activated.”

Then he clicked **Submit Ticket**.

That single click triggered an entire intelligent system working behind the scenes.

---

## Step 1: The Birth of a Ticket

The system instantly created a structured support ticket:

| Field | Value |
|--------|--------|
| Ticket ID | TKT-45821 |
| Status | Open |
| Priority | Not yet assigned |
| Category | Not yet determined |
| Timestamp | Recorded |

But unlike a traditional system, this was not just stored in a database.

The ticket immediately entered an **AI processing pipeline**.

---

## Step 2: The AI Reads Like a Human

Within milliseconds, the AI system analyzed Rahim’s message—not just as text, but as **intent**.

It understood:

- He made a payment
- The service is not activated
- The tone of the message shows frustration
- The issue may be time-sensitive and financial

So the system automatically decided:

- **Category** → Billing & Payment Issue
- **Priority** → High
- **Sentiment** → Negative (frustrated user)

This happened without any human intervention.

---

## Step 3: Intelligent Decision Making (Like a Support Manager)

Now the system acted like an experienced support manager.

It asked itself:

- Which agent has expertise in billing issues?
- Who currently has the lowest workload?
- Which ticket needs fastest attention due to SLA rules?

Based on this, it automatically assigned the ticket to an available agent named **Sara**.

At the same time, Sara received a notification:

> “High Priority Billing ticket assigned to you (TKT-45821). Customer is experiencing payment activation failure.”

She already had context before even opening the ticket.

---

## Step 4: The Agent Gets AI Superpowers

When Sara opened the ticket, she didn’t start from scratch.

The system immediately supported her with intelligence:

### Similar case retrieval

It showed:

- 3 similar past payment failure cases
- Their resolutions
- Average resolution time

### AI suggestion engine

It recommended:

> “Check payment gateway transaction status and verify service activation queue delay.”

### Auto-drafted response

It even suggested a reply:

> “We are currently verifying your payment status. We will update you shortly.”

This reduced Sara’s effort significantly and improved response speed.

---

## Step 5: Continuous Customer Communication

Meanwhile, Rahim was not left in silence.

He received real-time updates:

- “Your ticket has been received successfully.”
- “An agent is currently working on your issue.”

He could also:

- Reply with additional information
- Upload payment proof
- Track ticket status anytime

This kept the experience transparent and stress-free.

---

## Step 6: Resolution Workflow in Action

Sara investigated the issue and found:

- Payment was successfully received
- Service activation failed due to a system delay in the backend queue

She fixed the issue and updated the ticket:

> “Your payment has been verified and your service has now been activated. We apologize for the inconvenience.”

The system automatically transitioned the ticket:

`Open` → `In Progress` → `Resolved`

---

## Step 7: Closure and Customer Satisfaction

Rahim checked his account again. The service was now active.

He marked the issue as resolved, and the ticket moved to:

**Closed**

The system also sent a final notification:

> “Your issue has been resolved. If you face any further problems, feel free to reopen the ticket.”

---

## Step 8: The System Learns from Every Interaction

What Rahim experienced felt simple—but behind the scenes, the system was learning continuously.

It stored:

- Ticket type (Billing issue)
- Resolution steps
- Time taken to resolve
- Agent performance
- Customer sentiment

This data feeds back into the AI system, improving:

- Future ticket classification accuracy
- Faster priority prediction
- Better response suggestions
- Smarter routing decisions

So the system becomes more intelligent with every complaint it resolves.

---

## Final Picture

From Rahim’s perspective, it was simple:

> “I raised a complaint and it got solved.”

But in reality, the system was:

- Understanding human language using AI
- Making intelligent decisions like a manager
- Helping agents like an assistant
- Tracking everything in real time
- Learning from every interaction

---

## One-Line Summary

**It is a self-improving AI-powered customer support system that understands customer complaints, automatically classifies and prioritizes them, intelligently routes them to agents, assists in resolution using AI suggestions, and continuously learns from past cases to improve future performance.**
