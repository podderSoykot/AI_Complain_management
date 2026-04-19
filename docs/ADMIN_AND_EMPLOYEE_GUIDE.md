# Admin & employee guide

This document splits guidance for **administrators** and **employees** (support agents and supervisors). Both use the same codebase; login type and role determine access.

**API prefix:** `/api/v1`  
**Auth:** `Authorization: Bearer <token>` after login.

---

## Part A — Administrators

### Login

1. Open the web app.
2. Set **Login Type** to **Admin**.
3. Sign in with an account whose role is **`admin`** (often bootstrapped via `ADMIN_EMAIL` / `ADMIN_PASSWORD` in server env, then change password in production).

### Dashboard (admin)

- **Overview:** Summary of context.
- **Admin** tab (visible for admins): operational tools — stats, ticket operations, AI tools as implemented in the UI.
- **Tickets:** Cross-cutting ticket view where provided.

### User management (UI pages)

| Page | Typical use |
|------|-------------|
| **List users** (`list-user.html`) | Browse company staff vs customers; refresh; actions as shown in the table. |
| **Create user** (`create-user.html`) | Create accounts with role **customer**, **support_agent**, **supervisor**, or **admin**. For **support_agent** / **supervisor**, set **department** (required). |

The form calls `POST /api/v1/users`. The page expects an **admin** session in the browser; ensure your deployment policy matches how open registration should be (the API layer may be extended to restrict who can create elevated roles).

### Ticket management (UI pages)

| Page | Typical use |
|------|-------------|
| **List tickets** (`list-ticket.html`) | See pending vs assigned tickets, assign agents, smart assign, close tickets, previews. |

### AI features (admin)

- **Admin AI chat** on a specific ticket and **Work with agent** (admin) target the newest open ticket — both need a working LLM configuration on the server.
- If the UI shows **AI assistant isn’t configured** or **`LLM_MODE=api requires OPENAI_API_KEY`**, configure the backend (README — `LLM_MODE`, `OPENAI_API_KEY`, or local Ollama settings).

### Environment reminders for production

- Strong **`JWT_SECRET_KEY`**, secure admin password, **`DATABASE_URL`** for Postgres (or SQLite for dev only).
- **CORS** must include your frontend origin (e.g. Vercel).

---

## Part B — Employees (support agents & supervisors)

### Login

1. Set **Login Type** to **Employee**.
2. Use an account with role **`support_agent`** or **`supervisor`** (created by an admin).

**Note:** The API only allows employee login for these roles (`POST /api/v1/users/login/employee`).

### Dashboard (employee)

- **Overview** may show **My assigned tickets** with a button to open the full assigned-ticket page.
- **Profile** / **Settings:** Same idea as customers — identity and local preferences.

### Assigned tickets page

- Open **My assigned tickets** (`my-assigned-tickets.html`) from the overview shortcut or direct URL.
- Lists tickets assigned to **you**; use **Refresh** to reload.
- Update **work status** where the UI provides controls (maps to assignee workflow APIs).

### What employees typically do

- Work items assigned by admins or by routing rules.
- Read ticket details, conversations, and attachments (within permissions).
- Update status fields the UI exposes for assignees.
- Use AI-assisted flows only if enabled on the server (same LLM configuration as admin).

### Limitations

- Employee login **rejects** `customer` and `admin` roles — use **General** or **Admin** login types for those roles.

---

## Shared troubleshooting

| Issue | Suggestion |
|-------|------------|
| 403 on employee login | Account must be `support_agent` or `supervisor`. |
| 403 on admin routes | Log in as **Admin** with an `admin` role user. |
| AI errors | Fix `LLM_MODE` / keys on the server (README). |
| Empty lists | Check tenant/role filters; confirm data exists in the database. |

For **customers**, see [User guide](./USER_GUIDE.md).
