# User guide (customer)

This guide is for **customers** using the web app: register, log in, manage profile, and work with complaints (tickets) and the AI assistant.

**API base URL:** Your deployment exposes routes under `/api/v1`. The UI uses the configured frontend API origin (see README — `VITE_API_ORIGIN` on Vercel).

---

## 1. Account

### Register

- Use the **Register** flow on the main dashboard if available, or call `POST /api/v1/users` with email, password, name, and role `customer` (as documented for your class assignment).
- Your **tenant** is derived from your email domain (`tenant_id`).

### Log in

1. Open the app (e.g. Vercel URL).
2. Choose **Login Type: General**.
3. Enter email and password.
4. After login you see the dashboard (Overview, Profile, Settings, Tickets).

**Roles:** General login is for **customer** accounts. If you use Admin or Employee login types, you need the matching role (this guide focuses on customers).

---

## 2. Overview & profile

- **Overview:** Shows your user name, role type, tenant, and auth status.
- **Profile:** View name, email, role, tenant. You can adjust display name locally where the UI allows (**Save Profile (Local)** stores preferences in the browser where implemented).
- **Settings:** Theme / UI options saved for this browser (where implemented).

---

## 3. Tickets (complaints)

### Create a ticket

1. Go to the **Tickets** section.
2. Fill in **title** and **description** (minimum lengths apply).
3. Optionally attach files (limits: max file size and count per ticket — see server config).
4. Submit. The system may run AI enrichment (category, priority, sentiment) when the backend and LLM are configured.

### View and update

- Open your ticket list and select a ticket to see status, assignment, and conversation thread.
- Reply in the conversation thread when the UI provides a message box.
- Use **Work with agent** (customer) to run the AI agent against your **latest open ticket** (see below).

### Attachments

- Download rules follow server permissions; use in-app download actions when shown.

---

## 4. AI: “Work with agent” (customer)

- Available to **customers** for automated help on the **latest non-closed ticket you reported**.
- Requires the server LLM to be configured (`LLM_MODE` and related env vars — see README).
- If you see errors such as **AI assistant isn’t configured**, ask the administrator to set **`LLM_MODE=api`** with **`OPENAI_API_KEY`**, or **`LLM_MODE=local`** with a running Ollama/LM Studio endpoint.

---

## 5. Logging out

- Use **Logout** in the header to clear the session for this app in the browser.

---

## 6. Troubleshooting

| Issue | What to try |
|-------|-------------|
| Cannot log in | Confirm email/password; use **General** login for customers. |
| CORS / network errors | Frontend URL must be allowed on the API (CORS). API URL must match deployment (`VITE_API_ORIGIN`). |
| AI features fail | Backend LLM env not set or wrong mode for hosting (see README). |
| 401 on ticket actions | Log in again; JWT may have expired (default session length is configured on the server). |

For **admins** and **employees** (agents), see [Admin & employee guide](./ADMIN_AND_EMPLOYEE_GUIDE.md).
