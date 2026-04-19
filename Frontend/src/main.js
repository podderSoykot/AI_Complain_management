import "./style.css";
import { previewTicketAttachment } from "./admin-pages-common.js";

const API_BASE = "http://127.0.0.1:8000/api/v1";
let accessToken = "";
let currentUser = null;
let currentLoginType = "general";
let currentRole = "guest";
const SESSION_KEY = "acm_session";
let adminStatsTimer = null;

document.querySelector("#app").innerHTML = `
  <div class="bg-glow bg-glow-1"></div>
  <div class="bg-glow bg-glow-2"></div>

  <header class="topbar">
    <div class="brand">
      <div class="brand-badge">AI</div>
      <div>
        <h1>Complaint Management</h1>
        <p>Smart Support Operations Dashboard</p>
      </div>
    </div>
    <nav id="headerNav" class="header-nav hidden">
      <button class="header-tab active" data-section="overviewSection">Overview</button>
      <button class="header-tab" data-section="profileSection">Profile</button>
      <button class="header-tab" data-section="settingsSection">Settings</button>
      <button class="header-tab" data-section="ticketSection">Tickets</button>
      <button class="header-tab admin-only-tab hidden" data-section="adminSection">Admin</button>
    </nav>
    <div class="topbar-right">
      <span id="roleBadge" class="role-badge hidden">Role: -</span>
      <button type="button" id="headerWorkWithAgentBtn" class="btn btn-primary btn-sm hidden">Work with agent</button>
      <div class="status-pill"><span class="dot"></span>API Ready</div>
      <button id="logoutTop" class="btn btn-danger btn-sm hidden">Logout</button>
    </div>
  </header>

  <div id="agentRunAlert" class="agent-run-alert hidden" role="alert" aria-live="polite">
    <div class="agent-run-alert__row">
      <div class="agent-run-alert__body">
        <strong id="agentRunAlertTitle" class="agent-run-alert__title"></strong>
        <p id="agentRunAlertMsg" class="agent-run-alert__msg"></p>
        <div id="agentRunAlertHint" class="agent-run-alert__hint hidden"></div>
      </div>
      <button type="button" id="agentRunAlertClose" class="btn btn-ghost btn-sm agent-run-alert__close" aria-label="Dismiss">×</button>
    </div>
  </div>

  <main id="authGate" class="auth-layout">
    <section class="card card-accent auth-card">
      <h2>Login</h2>
      <p class="muted">Login first to access the dashboard.</p>
      <form id="loginForm" class="form-grid">
        <label>Email<input id="loginEmail" type="email" required placeholder="admin@example.com" /></label>
        <label>Password<input id="loginPassword" type="password" required placeholder="••••••••" /></label>
        <label>Login Type
          <select id="loginType">
            <option value="general">General</option>
            <option value="admin">Admin</option>
            <option value="employee">Employee</option>
          </select>
        </label>
        <button type="submit" class="btn btn-primary">Login</button>
      </form>
      <div id="loginResult" class="result"></div>
    </section>
  </main>

  <main id="dashboard" class="dashboard hidden">
    <section class="content">
      <section id="overviewSection" class="content-section card">
        <h2>Overview</h2>
        <p class="muted">Quick view of current login context and platform capabilities.</p>
        <div class="stat-grid">
          <div class="stat-box">
            <span>User</span>
            <strong id="overviewUser">-</strong>
          </div>
          <div class="stat-box">
            <span>Role Type</span>
            <strong id="overviewRoleType">-</strong>
          </div>
          <div class="stat-box">
            <span>Tenant</span>
            <strong id="overviewTenant">-</strong>
          </div>
          <div class="stat-box">
            <span>Auth Status</span>
            <strong>Authenticated</strong>
          </div>
        </div>
        <div id="employeeTicketsNavCard" class="employee-overview-actions hidden">
          <h3>My assigned tickets</h3>
          <p class="muted">Open the full list of tickets assigned to you (active, resolved, and closed history).</p>
          <button type="button" id="employeeAssignedTicketsBtn" class="btn btn-primary">Open assigned tickets page</button>
        </div>
      </section>

      <section id="profileSection" class="content-section card hidden">
        <h2>User Profile</h2>
        <p class="muted">Basic profile and account identity details.</p>
        <form id="profileForm" class="form-grid">
          <label>Full Name<input id="profileName" type="text" placeholder="Your name" /></label>
          <label>Email<input id="profileEmail" type="email" disabled /></label>
          <label>Role Type<input id="profileRoleType" type="text" disabled /></label>
          <label>Tenant ID<input id="profileTenant" type="text" disabled /></label>
          <button type="submit" class="btn btn-secondary">Save Profile (Local)</button>
        </form>
        <div id="profileResult" class="result"></div>
      </section>

      <section id="settingsSection" class="content-section card settings-page hidden">
        <header class="settings-head">
          <div class="settings-head-icon" aria-hidden="true">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="3"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>
          </div>
          <div class="settings-head-text">
            <h2 class="settings-title">Settings</h2>
            <p class="settings-lead">Choose how the dashboard looks and feels. Save to apply for this browser.</p>
          </div>
        </header>
        <form id="settingsForm" class="settings-form">
          <div class="settings-panel">
            <h3 class="settings-group-title">Appearance</h3>
            <p class="settings-group-desc">Light workspace with a dark or midnight color theme.</p>
            <label class="settings-field-label" for="settingTheme">Color theme</label>
            <div class="settings-theme-wrap">
              <select id="settingTheme" class="settings-select">
                <option value="dark">Dark (default)</option>
                <option value="midnight">Midnight</option>
              </select>
              <span class="settings-theme-hint" id="settingThemeHint">Soft light page with slate accents.</span>
            </div>
          </div>
          <div class="settings-panel">
            <h3 class="settings-group-title">Layout</h3>
            <p class="settings-group-desc">Optional density and notification behaviour.</p>
            <div class="settings-toggle-list">
              <div class="settings-toggle-row">
                <label class="settings-toggle">
                  <input id="settingNotify" type="checkbox" class="settings-toggle-input" />
                  <span class="settings-switch" aria-hidden="true"></span>
                  <span class="settings-toggle-copy">
                    <strong class="settings-toggle-name">Notification preview</strong>
                    <span class="settings-toggle-desc">Reserved for future toast and banner previews in the UI.</span>
                  </span>
                </label>
              </div>
              <div class="settings-toggle-row">
                <label class="settings-toggle">
                  <input id="settingCompact" type="checkbox" class="settings-toggle-input" />
                  <span class="settings-switch" aria-hidden="true"></span>
                  <span class="settings-toggle-copy">
                    <strong class="settings-toggle-name">Compact spacing</strong>
                    <span class="settings-toggle-desc">Tighter padding on cards for more content on one screen.</span>
                  </span>
                </label>
              </div>
            </div>
          </div>
          <div class="settings-actions">
            <button type="submit" class="btn btn-primary settings-save">Save settings</button>
          </div>
        </form>
        <div id="settingsResult" class="result settings-result"></div>
      </section>

      <section id="ticketSection" class="content-section card card-wide ticket-page hidden">
        <header class="ticket-page-head">
          <h2>Tickets</h2>
          <p class="muted ticket-page-lead">Open a complaint, attach files, update workflow, and keep the whole thread in one view.</p>
        </header>

        <div class="ticket-page-layout">
          <div class="ticket-page-col ticket-page-col--main">
            <article class="ticket-card ticket-card--elevated ticket-card--create">
              <div class="create-head">
                <div class="create-head-icon" aria-hidden="true">
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>
                </div>
                <div class="create-head-text">
                  <span class="create-head-eyebrow">New case</span>
                  <h3 class="create-head-title">Create a ticket</h3>
                  <p class="create-head-lead">A clear subject and steps help the team route and resolve your request faster.</p>
                </div>
              </div>
              <div class="ticket-card-body create-body">
                <form id="ticketForm" class="create-form">
                  <div class="create-layout">
                    <div class="create-main">
                      <label class="create-field">
                        <span class="create-label">Subject <span class="create-req">*</span></span>
                        <input id="ticketTitle" type="text" required placeholder="e.g. Login fails after password reset" class="create-input create-input--title" />
                      </label>
                      <label class="create-field">
                        <span class="create-label">What happened <span class="create-req">*</span></span>
                        <textarea id="ticketDescription" rows="6" required placeholder="Include what you expected, what you saw, dates or order IDs if relevant, and what you need from support." class="create-input create-input--body"></textarea>
                      </label>
                      <div class="create-field">
                        <span class="create-label">Attachments <span class="create-opt">optional</span></span>
                        <label class="create-drop">
                          <input id="ticketFiles" type="file" multiple accept=".pdf,.png,.jpg,.jpeg,.webp,.gif,.txt,.csv,.doc,.docx,.xls,.xlsx,image/*" class="create-drop-input" />
                          <span class="create-drop-ui">
                            <span class="create-drop-icon" aria-hidden="true">
                              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12"/></svg>
                            </span>
                            <span class="create-drop-title">Upload files</span>
                            <span class="create-drop-hint">Click this area to choose files — PDF, images, Word/Excel, text. Up to 8 files, 10 MB each.</span>
                          </span>
                        </label>
                      </div>
                    </div>
                    <aside class="create-aside" aria-label="Tips">
                      <div class="create-tip">
                        <span class="create-tip-num">1</span>
                        <div>
                          <strong>One issue per ticket</strong>
                          <p>Split unrelated problems so each can be tracked and closed.</p>
                        </div>
                      </div>
                      <div class="create-tip">
                        <span class="create-tip-num">2</span>
                        <div>
                          <strong>Reproduce steps</strong>
                          <p>Short numbered steps save back-and-forth and speed up fixes.</p>
                        </div>
                      </div>
                      <div class="create-tip">
                        <span class="create-tip-num">3</span>
                        <div>
                          <strong>Add proof</strong>
                          <p>Screenshots or exports often resolve disputes in one round.</p>
                        </div>
                      </div>
                    </aside>
                  </div>
                  <div class="create-actions">
                    <p class="create-actions-note">By submitting, this ticket is recorded in your tenant for the support team.</p>
                    <button type="submit" class="btn btn-primary create-submit">
                      <span>Submit ticket</span>
                      <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true" fill="currentColor"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
                    </button>
                  </div>
                </form>
                <div id="ticketResult" class="result ticket-inline-result create-result"></div>
              </div>
            </article>

            <article id="ticketDocsPanel" class="ticket-card ticket-card--soft hidden">
              <div class="ticket-card-head">
                <span class="ticket-card-eyebrow">Files</span>
                <h3 class="ticket-card-title">Supporting documents</h3>
                <p class="muted ticket-card-desc" id="ticketDocsHelp">Open a ticket from “My assigned tickets” or enter an ID in Conversation below, then load files.</p>
              </div>
              <div class="ticket-card-body">
                <ul id="ticketDocsList" class="ticket-docs-list"></ul>
              </div>
            </article>
          </div>

          <aside class="ticket-page-col ticket-page-col--side">
            <article id="employeeTools" class="ticket-card ticket-card--soft hidden">
              <div class="ticket-card-head">
                <span class="ticket-card-eyebrow">Staff</span>
                <h3 class="ticket-card-title">Workflow status</h3>
                <p class="muted ticket-card-desc">Move the ticket through review → in progress → resolved.</p>
              </div>
              <div class="ticket-card-body">
                <form id="ticketWorkStatusForm" class="form-grid ticket-side-form">
                  <div class="ticket-field-row">
                    <label>Ticket ID<input id="workTicketId" type="number" min="1" required /></label>
                    <label>Status
                      <select id="workStatus" required>
                        <option value="in_review">In review</option>
                        <option value="in_progress">In progress</option>
                        <option value="resolved">Resolved</option>
                      </select>
                    </label>
                  </div>
                  <button type="submit" class="btn btn-secondary">Update status</button>
                </form>
                <div id="workStatusResult" class="result ticket-inline-result"></div>
              </div>
            </article>

            <article id="adminCloseTools" class="ticket-card ticket-card--accent hidden">
              <div class="ticket-card-head">
                <span class="ticket-card-eyebrow">Admin</span>
                <h3 class="ticket-card-title">Close ticket</h3>
                <p class="muted ticket-card-desc">Close after support has marked the ticket resolved.</p>
              </div>
              <div class="ticket-card-body">
                <form id="adminCloseForm" class="form-grid ticket-side-form">
                  <label>Ticket ID<input id="adminCloseTicketId" type="number" min="1" required /></label>
                  <button type="submit" class="btn btn-danger">Close ticket</button>
                </form>
                <div id="adminCloseResult" class="result ticket-inline-result"></div>
              </div>
            </article>
          </aside>
        </div>

        <article class="ticket-card ticket-card--thread ticket-card--msgr">
          <div class="ticket-card-body ticket-card-body--flush">
            <form id="conversationForm" class="msgr" autocomplete="off">
              <header class="msgr-header">
                <div class="msgr-header-info">
                  <div class="msgr-header-avatar" aria-hidden="true">#</div>
                  <div class="msgr-header-text">
                    <div class="msgr-header-title">Ticket messages</div>
                    <div class="msgr-header-sub">Messenger-style thread</div>
                  </div>
                </div>
                <div class="msgr-header-actions">
                  <div class="msgr-ticket-pill">
                    <span class="msgr-ticket-pill-label">Ticket</span>
                    <input id="conversationTicketId" class="msgr-ticket-pill-input" type="number" min="1" required placeholder="ID" />
                  </div>
                  <button type="button" id="loadConversationBtn" class="msgr-icon-btn" title="Refresh thread" aria-label="Refresh thread">
                    <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M17.65 6.35A7.958 7.958 0 0012 4V1L7 6l5 5V8c2.76 0 5 2.24 5 5 0 1.13-.37 2.16-1 3l1.47 1.47A7.958 7.958 0 0020 13c0-2.49-1.01-4.75-2.65-6.35zM6.35 17.65A7.958 7.958 0 0012 20v3l5-5-5-5v2c-2.76 0-5-2.24-5-5 0-1.13.37-2.16 1-3L5.53 8.53A7.958 7.958 0 004 11c0 2.49 1.01 4.75 2.65 6.35z"/></svg>
                  </button>
                  <button type="button" id="loadTicketDocsBtn" class="msgr-icon-btn" title="Attachments" aria-label="Attachments">
                    <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M16.5 6v11.5c0 2.21-1.79 4-4 4s-4-1.79-4-4V5a2.5 2.5 0 015 0v10.5a1 1 0 11-2 0V6H10v9.5a2.5 2.5 0 005 0V5a4.5 4.5 0 00-9 0v12.5a5.5 5.5 0 0011 0V6h-1.5z"/></svg>
                  </button>
                </div>
              </header>
              <div id="conversationResult" class="msgr-thread" aria-live="polite" aria-relevant="additions">
                <div class="msgr-empty">
                  <p>Enter a ticket number, then press <strong>Refresh</strong>. Your messages appear on the <strong>right</strong> like Messenger.</p>
                </div>
              </div>
              <footer class="msgr-footer">
                <div class="msgr-compose">
                  <select id="conversationType" class="msgr-type" required title="Message type">
                    <option value="note">Note</option>
                    <option value="question">Question</option>
                    <option value="document_request">Document request</option>
                    <option value="user_reply">Reply</option>
                    <option value="resolution_note">Resolution</option>
                  </select>
                  <div class="msgr-input-wrap">
                    <textarea id="conversationMessage" class="msgr-textarea" rows="1" required placeholder="Aa"></textarea>
                  </div>
                  <button type="submit" class="msgr-send" title="Send" aria-label="Send">
                    <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
                  </button>
                </div>
              </footer>
            </form>
          </div>
        </article>
      </section>

      <section id="adminSection" class="content-section card hidden">
        <h2>Admin Actions</h2>
        <p class="muted">Admin-only controls: user management, platform insights, and global ticket operations.</p>
        <div class="admin-hero-actions">
          <button id="adminHeroCreateUser" class="btn btn-secondary">Create User</button>
          <button id="adminHeroListUser" class="btn btn-ghost">List User</button>
          <button id="adminHeroTicketList" class="btn btn-ghost">Ticket List</button>
        </div>
        <div>
          <h3>Admin Overview</h3>
          <div class="admin-live-head">
            <p class="muted">Live stats auto-refresh every 15 seconds.</p>
            <span class="live-badge"><span class="live-dot"></span>Live</span>
          </div>
          <div id="adminResult" class="result large">Loading live stats...</div>
        </div>
        <div class="ticket-subpanel">
          <div class="panel-head">
            <h3>Resolved Waiting for Close</h3>
            <button id="refreshResolvedQueueBtn" class="btn btn-ghost">Refresh</button>
          </div>
          <p class="muted">Tickets the assigned employee marked <strong>resolved</strong>. Admin can close after review (tickets without an assignee cannot be closed).</p>
          <div id="adminResolvedQueue" class="result large">Loading resolved queue...</div>
        </div>
      </section>
    </section>
  </main>
`;

const byId = (id) => document.getElementById(id);
const authGate = byId("authGate");
const dashboard = byId("dashboard");
const logoutTop = byId("logoutTop");
const roleBadge = byId("roleBadge");
const headerNav = byId("headerNav");
const headerTabs = Array.from(document.querySelectorAll(".header-tab"));
const sectionIds = [
  "overviewSection",
  "profileSection",
  "settingsSection",
  "ticketSection",
  "adminSection",
];

const setResult = (id, data) => {
  const el = byId(id);
  el.classList.remove("result-ok", "result-error");
  if (typeof data === "object" && data !== null && "status" in data) {
    if (data.status >= 200 && data.status < 300) el.classList.add("result-ok");
    if (data.status >= 400) el.classList.add("result-error");
  }
  el.textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
};

const showToast = (message, type = "success") => {
  const existing = document.querySelector(".toast");
  if (existing) existing.remove();

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);

  requestAnimationFrame(() => toast.classList.add("show"));
  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => toast.remove(), 220);
  }, 2200);
};

const renderAdminView = (kind, result, targetOverride = null) => {
  const targetMap = {
    stats: "adminResult",
    users: "adminResult",
    tickets: "adminResult",
  };
  const el = byId(targetOverride || targetMap[kind] || "adminResult");
  if (!el) return;
  if (result.status < 200 || result.status >= 300) {
    el.innerHTML = `<div class="admin-error">Request failed (${result.status})<br/>${JSON.stringify(result.data)}</div>`;
    return;
  }

  if (kind === "stats") {
    const d = result.data || {};
    const totalTickets = Number(d.tickets_total ?? 0);
    const resolved = Number(d.resolved_or_closed_tickets ?? 0);
    const openAssigned = Number(d.open_or_assigned_tickets ?? 0);
    const resolvedPercent = totalTickets > 0 ? Math.min(100, Math.round((resolved / totalTickets) * 100)) : 0;
    const openPercent = totalTickets > 0 ? Math.min(100, Math.round((openAssigned / totalTickets) * 100)) : 0;
    const updatedAt = new Date().toLocaleTimeString();
    el.innerHTML = `
      <div class="admin-kpi-grid colorful">
        <div class="admin-kpi admin-kpi-users">
          <span>Total Users</span>
          <strong>${d.users_total ?? 0}</strong>
        </div>
        <div class="admin-kpi admin-kpi-tickets">
          <span>Total Tickets</span>
          <strong>${d.tickets_total ?? 0}</strong>
        </div>
        <div class="admin-kpi admin-kpi-open">
          <span>Open/Assigned</span>
          <strong>${openAssigned}</strong>
          <small>${openPercent}% of all tickets</small>
        </div>
        <div class="admin-kpi admin-kpi-resolved">
          <span>Resolved/Closed</span>
          <strong>${resolved}</strong>
          <small>${resolvedPercent}% resolved</small>
        </div>
      </div>
      <div class="admin-progress-wrap">
        <div class="admin-progress-label">
          <span>Resolution Progress</span>
          <span>${resolvedPercent}%</span>
        </div>
        <div class="admin-progress-track">
          <div class="admin-progress-bar" style="width:${resolvedPercent}%"></div>
        </div>
      </div>
      <div class="admin-updated-at">
        Updated: ${updatedAt}
      </div>
    `;
    return;
  }

  if (kind === "users" && Array.isArray(result.data)) {
    const rows = result.data
      .slice(0, 50)
      .map(
        (u) => `
        <tr>
          <td>${u.id}</td>
          <td>${u.full_name ?? "-"}</td>
          <td>${u.email ?? "-"}</td>
          <td><span class="pill">${u.role ?? "-"}</span></td>
          <td>${u.department?.trim() ? u.department : "—"}</td>
          <td>${u.tenant_id ?? "-"}</td>
          <td>${u.is_active === 1 ? "Active" : "Inactive"}</td>
        </tr>`
      )
      .join("");
    el.innerHTML = `
      <div class="admin-table-wrap">
        <table class="admin-table">
          <thead><tr><th>ID</th><th>Name</th><th>Email</th><th>Role</th><th>Department</th><th>Tenant</th><th>Status</th></tr></thead>
          <tbody>${rows || `<tr><td colspan="7">No users found.</td></tr>`}</tbody>
        </table>
      </div>
    `;
    return;
  }

  if (kind === "tickets" && Array.isArray(result.data)) {
    const rows = result.data
      .slice(0, 50)
      .map(
        (t) => `
        <tr>
          <td>${t.id}</td>
          <td>${t.title ?? "-"}</td>
          <td><span class="pill">${t.category ?? "-"}</span></td>
          <td>${t.priority ?? "-"}</td>
          <td>${t.status ?? "-"}</td>
          <td>${t.assignee_id ?? "-"}</td>
        </tr>`
      )
      .join("");
    el.innerHTML = `
      <div class="admin-table-wrap">
        <table class="admin-table">
          <thead><tr><th>ID</th><th>Title</th><th>Category</th><th>Priority</th><th>Status</th><th>Assignee</th></tr></thead>
          <tbody>${rows || `<tr><td colspan="6">No tickets found.</td></tr>`}</tbody>
        </table>
      </div>
    `;
    return;
  }

  el.textContent = JSON.stringify(result.data, null, 2);
};
const authHeaders = () =>
  accessToken ? { Authorization: `Bearer ${accessToken}`, "Content-Type": "application/json" } : { "Content-Type": "application/json" };

const escapeHtml = (s) =>
  String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

const detailFromApiData = (data) => {
  if (!data || typeof data !== "object") return "";
  const d = data.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => (typeof x === "string" ? x : x?.msg || JSON.stringify(x))).join("; ");
  if (d != null) return typeof d === "object" ? JSON.stringify(d) : String(d);
  return "";
};

const hideAgentRunAlert = () => {
  byId("agentRunAlert")?.classList.add("hidden");
};

const showAgentRunAlertFromResult = (result) => {
  const box = byId("agentRunAlert");
  const titleEl = byId("agentRunAlertTitle");
  const msgEl = byId("agentRunAlertMsg");
  const hintEl = byId("agentRunAlertHint");
  if (!box || !titleEl || !msgEl || !hintEl) return;
  const detail = detailFromApiData(result.data);
  const msg = detail.trim() || `Request failed (HTTP ${result.status}).`;
  const looksLlm = /LLM_MODE|OPENAI|Ollama|LM Studio|api key/i.test(detail);
  titleEl.textContent = looksLlm ? "AI assistant isn’t configured" : "Assistant request failed";
  msgEl.textContent = msg;
  if (looksLlm) {
    hintEl.classList.remove("hidden");
    hintEl.innerHTML = `
      <p class="agent-run-alert__hint-lead">On the server, use one of these setups:</p>
      <ul class="agent-run-alert__codes">
        <li><span class="agent-run-alert__code">LLM_MODE=local</span> — run Ollama or LM Studio locally</li>
        <li><span class="agent-run-alert__code">LLM_MODE=api</span> + <span class="agent-run-alert__code">OPENAI_API_KEY</span> — cloud model</li>
      </ul>`;
  } else {
    hintEl.classList.add("hidden");
    hintEl.innerHTML = "";
  }
  box.classList.remove("hidden");
};

function renderTicketDocsList(ticketId, attachments) {
  const panel = byId("ticketDocsPanel");
  const list = byId("ticketDocsList");
  const help = byId("ticketDocsHelp");
  if (!panel || !list || !help) return;
  panel.classList.remove("hidden");
  const atts = attachments || [];
  help.textContent = atts.length
    ? `Ticket #${ticketId} — ${atts.length} supporting file(s). Use View to open here (PDF / image / text).`
    : `Ticket #${ticketId} — no supporting documents uploaded.`;
  list.innerHTML = atts.length
    ? atts
        .map(
          (a) =>
            `<li><span class="ticket-attachment-filename">${escapeHtml(a.original_filename)}</span> <span class="muted">(${(a.size_bytes / 1024).toFixed(1)} KB)</span> <button type="button" class="btn btn-secondary btn-sm ticket-doc-preview" data-tid="${ticketId}" data-aid="${a.id}" data-fn="${encodeURIComponent(a.original_filename)}" data-ct="${encodeURIComponent(a.content_type || "")}">View</button></li>`,
        )
        .join("")
    : "";
}

async function loadTicketDocsForWork(ticketId) {
  const result = await request(`/tickets/${ticketId}`, { headers: authHeaders() });
  if (result.status < 200 || result.status >= 300) {
    byId("ticketDocsPanel")?.classList.remove("hidden");
    byId("ticketDocsList").innerHTML = "";
    byId("ticketDocsHelp").textContent = `Could not load ticket #${ticketId} (HTTP ${result.status}).`;
    return;
  }
  renderTicketDocsList(ticketId, result.data?.attachments || []);
}

byId("ticketSection")?.addEventListener("click", async (e) => {
  const btn = e.target.closest(".ticket-doc-preview");
  if (!btn) return;
  const tid = Number(btn.dataset.tid);
  const aid = Number(btn.dataset.aid);
  const fn = decodeURIComponent(btn.dataset.fn || "file");
  const ct = decodeURIComponent(btn.dataset.ct || "");
  try {
    await previewTicketAttachment(tid, aid, { original_filename: fn, content_type: ct });
  } catch (err) {
    showToast(err?.message || "Could not open file", "error");
  }
});
const updateTokenView = () => {
  return;
};

const setAuthState = (isLoggedIn) => {
  authGate.classList.toggle("hidden", isLoggedIn);
  dashboard.classList.toggle("hidden", !isLoggedIn);
  logoutTop.classList.toggle("hidden", !isLoggedIn);
  roleBadge.classList.toggle("hidden", !isLoggedIn);
  headerNav.classList.toggle("hidden", !isLoggedIn);
  if (!isLoggedIn) hideAgentRunAlert();
  const headerAgentBtn = byId("headerWorkWithAgentBtn");
  if (headerAgentBtn) {
    const show =
      isLoggedIn && (currentRole === "customer" || currentRole === "admin");
    headerAgentBtn.classList.toggle("hidden", !show);
  }
};

const decodeJwtPayload = (token) => {
  try {
    const part = token.split(".")[1];
    const decoded = atob(part.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(decoded);
  } catch {
    return null;
  }
};

const isTokenValid = (token) => {
  const payload = decodeJwtPayload(token);
  if (!payload) return false;
  if (!payload.exp) return true;
  const now = Math.floor(Date.now() / 1000);
  return payload.exp > now;
};

const tenantFromEmail = (email) => {
  if (!email || !email.includes("@")) return "public";
  return email.split("@")[1].toLowerCase().replace(/\./g, "_").replace(/-/g, "_");
};

const hydrateUserInfo = () => {
  const email = currentUser?.email || "-";
  const tenant = tenantFromEmail(currentUser?.email || "");
  byId("overviewUser").textContent = email;
  byId("overviewRoleType").textContent = currentRole;
  byId("overviewTenant").textContent = tenant;

  byId("profileEmail").value = email;
  byId("profileRoleType").value = currentRole;
  byId("profileTenant").value = tenant;
  byId("profileName").value = localStorage.getItem("profile_name") || "";
  roleBadge.textContent = `Role: ${currentRole}`;
};

const syncThemeHint = () => {
  const hint = byId("settingThemeHint");
  const sel = byId("settingTheme");
  if (!hint || !sel) return;
  hint.textContent =
    sel.value === "midnight"
      ? "Deep near-black surfaces with softer contrast."
      : "Soft light page with slate accents (default).";
};

const applySettings = () => {
  const compact = localStorage.getItem("setting_compact") === "1";
  document.body.classList.toggle("compact", compact);

  const theme = localStorage.getItem("setting_theme") || "dark";
  document.body.dataset.theme = theme;
  byId("settingTheme").value = theme;
  byId("settingNotify").checked = localStorage.getItem("setting_notify") === "1";
  byId("settingCompact").checked = compact;
  syncThemeHint();
};

const switchSection = (targetId) => {
  for (const id of sectionIds) {
    byId(id).classList.toggle("hidden", id !== targetId);
  }
  headerTabs.forEach((btn) => btn.classList.toggle("active", btn.dataset.section === targetId));
  localStorage.setItem("active_section", targetId);
};

const formatConversationType = (t) => {
  const key = String(t || "note").toLowerCase();
  const labels = {
    note: "Note",
    question: "Question",
    document_request: "Document request",
    user_reply: "User reply",
    resolution_note: "Resolution",
    ai_admin: "Assistant",
    ai_customer: "Assistant",
  };
  return labels[key] || key.replace(/_/g, " ");
};

const paintConversationApiError = (result) => {
  const el = byId("conversationResult");
  if (!el) return;
  el.className = "msgr-thread msgr-thread--error";
  const msg =
    detailFromApiData(result.data)?.trim() ||
    (typeof result.data?.detail === "string" ? result.data.detail : "") ||
    `Something went wrong (${result.status})`;
  el.innerHTML = `<div class="msgr-error" role="alert">
    <div class="msgr-error-title">Couldn’t load or send</div>
    <p class="msgr-error-msg">${escapeHtml(msg)}</p>
  </div>`;
};

const applyRoleUI = () => {
  const adminHeaderTabs = headerTabs.filter((btn) => btn.classList.contains("admin-only-tab"));
  const isAdmin = currentRole === "admin";
  adminHeaderTabs.forEach((btn) => btn.classList.toggle("hidden", !isAdmin));
  const employeeTools = byId("employeeTools");
  const adminCloseTools = byId("adminCloseTools");
  const employeeTicketsNavCard = byId("employeeTicketsNavCard");
  if (employeeTools) employeeTools.classList.toggle("hidden", currentLoginType !== "employee");
  if (employeeTicketsNavCard) employeeTicketsNavCard.classList.toggle("hidden", currentLoginType !== "employee");
  if (adminCloseTools) adminCloseTools.classList.toggle("hidden", !isAdmin);
  if (!isAdmin && byId("adminSection") && !byId("adminSection").classList.contains("hidden")) {
    switchSection("overviewSection");
  }
};

const msgrAvatarLetter = (msg, isAssistant) => {
  if (isAssistant) return "AI";
  const r = String(msg.sender_role || "u").replace(/[^a-z]/gi, "");
  return (r.charAt(0) || "U").toUpperCase();
};

const renderConversation = (result) => {
  const el = byId("conversationResult");
  if (!el) return;
  if (result.status < 200 || result.status >= 300) {
    paintConversationApiError(result);
    return;
  }
  el.className = "msgr-thread";
  const messages = Array.isArray(result.data) ? result.data : [];
  if (!messages.length) {
    el.innerHTML = `<div class="msgr-empty"><p>No messages yet. Type below and send to start.</p></div>`;
    return;
  }
  const rows = messages.map((msg) => {
    const isAssistant =
      msg.sender_role === "assistant" || /^ai_/i.test(String(msg.message_type || ""));
    const isMine = !isAssistant && msg.sender_role === currentRole;
    const typeLabel = formatConversationType(msg.message_type);
    const createdAt = msg.created_at
      ? new Date(msg.created_at).toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" })
      : "";
    const meta = `${escapeHtml(typeLabel)}${createdAt ? ` · ${escapeHtml(createdAt)}` : ""}`;
    const body = escapeHtml(msg.message || "");
    if (isMine) {
      return `<div class="msgr-row msgr-row--out">
        <div class="msgr-stack msgr-stack--out">
          <div class="msgr-bubble msgr-bubble--out">${body}</div>
          <div class="msgr-meta msgr-meta--out">${meta}</div>
        </div>
      </div>`;
    }
    const name = isAssistant
      ? "Assistant"
      : `${String(msg.sender_role || "user")
          .replace(/_/g, " ")
          .replace(/\b\w/g, (c) => c.toUpperCase())}`;
    const letter = msgrAvatarLetter(msg, isAssistant);
    const bubbleCls = isAssistant ? "msgr-bubble msgr-bubble--in msgr-bubble--bot" : "msgr-bubble msgr-bubble--in";
    return `<div class="msgr-row msgr-row--in">
      <div class="msgr-avatar" aria-hidden="true">${escapeHtml(letter)}</div>
      <div class="msgr-stack msgr-stack--in">
        <div class="msgr-sender">${escapeHtml(name)}</div>
        <div class="${bubbleCls}">${body}</div>
        <div class="msgr-meta msgr-meta--in">${meta}</div>
      </div>
    </div>`;
  });
  el.innerHTML = `<div class="msgr-thread-inner">${rows.join("")}</div>`;
  requestAnimationFrame(() => {
    el.scrollTop = el.scrollHeight;
  });
};

const renderResolvedQueue = (result) => {
  const el = byId("adminResolvedQueue");
  if (!el) return;
  if (result.status < 200 || result.status >= 300 || !Array.isArray(result.data)) {
    setResult("adminResolvedQueue", result);
    return;
  }

  const resolved = result.data.filter((t) => t.status === "resolved" && t.assignee_id);
  if (!resolved.length) {
    el.innerHTML = `<div class="conversation-empty">No employee-resolved tickets waiting for close.</div>`;
    return;
  }

  const assigneeCell = (t) => {
    const name = (t.assignee_full_name || "").trim();
    const dept = (t.assignee_department || "").trim();
    if (name && dept) return `${name} <span class="muted">(${dept})</span>`;
    if (name) return name;
    return `User #${t.assignee_id}`;
  };

  const rows = resolved
    .slice(0, 100)
    .map(
      (t) => `
        <tr>
          <td>${t.id}</td>
          <td>${t.title ?? "-"}</td>
          <td>${t.priority ?? "-"}</td>
          <td>${assigneeCell(t)}</td>
          <td><span class="pill">resolved</span></td>
          <td><button class="btn btn-danger btn-sm admin-close-ticket-btn" data-ticket-id="${t.id}">Close</button></td>
        </tr>
      `
    )
    .join("");

  el.innerHTML = `
    <div class="admin-table-wrap">
      <table class="admin-table">
        <thead><tr><th>ID</th><th>Title</th><th>Priority</th><th>Resolved by (employee)</th><th>Status</th><th>Action</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
  `;
};

const loadAdminResolvedQueue = async () => {
  if (currentRole !== "admin") return;
  const result = await request("/admin/tickets?limit=500", { headers: authHeaders() });
  renderResolvedQueue(result);
};

const stopAdminStatsAutoRefresh = () => {
  if (adminStatsTimer) {
    clearInterval(adminStatsTimer);
    adminStatsTimer = null;
  }
};

const startAdminStatsAutoRefresh = () => {
  stopAdminStatsAutoRefresh();
  if (currentRole !== "admin") return;

  const refresh = async () => {
    const res = await request("/admin/stats", { headers: authHeaders() });
    renderAdminView("stats", res);
    await loadAdminResolvedQueue();
  };

  refresh();
  adminStatsTimer = setInterval(refresh, 15000);
};

const saveSession = () => {
  if (!accessToken || !currentUser?.email) return;
  const state = {
    token: accessToken,
    email: currentUser.email,
    loginType: currentLoginType,
    role: currentRole,
  };
  localStorage.setItem(SESSION_KEY, JSON.stringify(state));
};

const clearSession = () => {
  localStorage.removeItem(SESSION_KEY);
};

const restoreSession = () => {
  const raw = localStorage.getItem(SESSION_KEY);
  if (!raw) return false;
  try {
    const saved = JSON.parse(raw);
    if (!saved?.token || !saved?.email) return false;
    if (!isTokenValid(saved.token)) {
      clearSession();
      return false;
    }
    accessToken = saved.token;
    currentUser = { email: saved.email };
    currentLoginType = saved.loginType || "general";
    currentRole = saved.role || decodeJwtPayload(saved.token)?.role || "customer";
    updateTokenView();
    hydrateUserInfo();
    applySettings();
    applyRoleUI();
    setAuthState(true);
    return true;
  } catch {
    clearSession();
    return false;
  }
};

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, options);
  const data = await res.json().catch(() => ({}));
  return { status: res.status, data };
}

byId("loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const email = byId("loginEmail").value.trim();
  const password = byId("loginPassword").value;
  const type = byId("loginType").value;

  let endpoint = "/users/login";
  if (type === "admin") endpoint = "/users/login/admin";
  if (type === "employee") endpoint = "/users/login/employee";

  const result = await request(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (result.status === 200 && result.data.access_token) {
    accessToken = result.data.access_token;
    const payload = decodeJwtPayload(accessToken);
    currentUser = { email: payload?.sub || email };
    currentLoginType = type;
    const fromApi = result.data.role;
    const fromJwt = payload?.role;
    currentRole =
      fromApi ||
      fromJwt ||
      (type === "admin" ? "admin" : type === "employee" ? "employee" : "customer");
    updateTokenView();
    hydrateUserInfo();
    applySettings();
    applyRoleUI();
    setAuthState(true);
    saveSession();
    startAdminStatsAutoRefresh();
  }
  setResult("loginResult", result);
});

byId("ticketForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData();
  fd.append("title", byId("ticketTitle").value.trim());
  fd.append("description", byId("ticketDescription").value.trim());
  const fileInput = byId("ticketFiles");
  if (fileInput?.files?.length) {
    for (let i = 0; i < fileInput.files.length; i += 1) {
      fd.append("files", fileInput.files[i]);
    }
  }
  const res = await fetch(`${API_BASE}/tickets`, {
    method: "POST",
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
    body: fd,
  });
  const data = await res.json().catch(() => ({}));
  const result = { status: res.status, data };
  byId("ticketResult").textContent = "";
  if (result.status >= 200 && result.status < 300) {
    const ticketId = result.data?.id;
    const n = result.data?.attachments?.length || 0;
    showToast(
      ticketId
        ? `Ticket #${ticketId} created${n ? ` with ${n} file(s)` : ""}.`
        : "Ticket created successfully",
      "success",
    );
    byId("ticketForm").reset();
    if (ticketId) {
      byId("ticketDocsPanel")?.classList.remove("hidden");
      renderTicketDocsList(ticketId, result.data?.attachments || []);
      const conv = byId("conversationTicketId");
      if (conv) conv.value = String(ticketId);
    }
  } else {
    showToast("Failed to create ticket. Please try again.", "error");
    setResult("ticketResult", result);
  }
});

byId("ticketWorkStatusForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const ticketId = Number(byId("workTicketId").value);
  const status = byId("workStatus").value;
  const result = await request(`/tickets/${ticketId}/work-status`, {
    method: "PATCH",
    headers: authHeaders(),
    body: JSON.stringify({ status }),
  });
  setResult("workStatusResult", result);
  if (result.status >= 200 && result.status < 300) {
    showToast(`Ticket #${ticketId} moved to ${status}`, "success");
  } else {
    showToast("Failed to update ticket workflow status", "error");
  }
});

byId("adminCloseForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const ticketId = Number(byId("adminCloseTicketId").value);
  const result = await request(`/admin/tickets/${ticketId}/close`, {
    method: "PATCH",
    headers: authHeaders(),
  });
  setResult("adminCloseResult", result);
  if (result.status >= 200 && result.status < 300) {
    showToast(`Ticket #${ticketId} closed by admin`, "success");
  } else {
    showToast("Failed to close ticket", "error");
  }
});

byId("conversationForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const ticketId = Number(byId("conversationTicketId").value);
  const message_type = byId("conversationType").value;
  const message = byId("conversationMessage").value.trim();
  const result = await request(`/tickets/${ticketId}/conversations`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ message_type, message }),
  });
  if (result.status >= 200 && result.status < 300) {
    byId("conversationMessage").value = "";
    showToast("Message sent to ticket conversation", "success");
    const refresh = await request(`/tickets/${ticketId}/conversations`, { headers: authHeaders() });
    renderConversation(refresh);
  } else {
    paintConversationApiError(result);
    showToast("Failed to send conversation message", "error");
  }
});

byId("loadConversationBtn").addEventListener("click", async () => {
  const ticketId = Number(byId("conversationTicketId").value);
  if (!ticketId) {
    showToast("Enter a ticket ID first", "error");
    return;
  }
  const result = await request(`/tickets/${ticketId}/conversations`, { headers: authHeaders() });
  renderConversation(result);
});

byId("loadTicketDocsBtn")?.addEventListener("click", async () => {
  const ticketId = Number(byId("conversationTicketId").value);
  if (!ticketId) {
    showToast("Enter a ticket ID first", "error");
    return;
  }
  await loadTicketDocsForWork(ticketId);
});

byId("headerWorkWithAgentBtn")?.addEventListener("click", async () => {
  const btn = byId("headerWorkWithAgentBtn");
  if (!btn || btn.classList.contains("hidden")) return;
  hideAgentRunAlert();
  if (currentRole === "admin") {
    btn.disabled = true;
    const result = await request(`/admin/tickets/ai/agent-run`, {
      method: "POST",
      headers: authHeaders(),
    });
    btn.disabled = false;
    if (result.status >= 200 && result.status < 300) {
      const tid = result.data?.ticket_id;
      const tidMsg = tid ? ` (#${tid})` : "";
      showToast(
        (result.data?.resolution_applied ? "Agent done — resolved" : "Agent done — saved") + tidMsg,
        "success",
      );
      if (tid) byId("conversationTicketId").value = String(tid);
    } else {
      showAgentRunAlertFromResult(result);
    }
    return;
  }
  if (currentRole !== "customer") return;
  btn.disabled = true;
  const result = await request(`/tickets/ai/agent-run`, {
    method: "POST",
    headers: authHeaders(),
  });
  btn.disabled = false;
  if (result.status >= 200 && result.status < 300) {
    const tid = result.data?.ticket_id;
    if (tid) byId("conversationTicketId").value = String(tid);
    showToast(tid ? `Agent টিকেট #${tid} এ উত্তর দিয়েছে` : "Agent replied", "success");
    if (tid) {
      const refresh = await request(`/tickets/${tid}/conversations`, { headers: authHeaders() });
      renderConversation(refresh);
    }
  } else {
    showAgentRunAlertFromResult(result);
  }
});

byId("agentRunAlertClose")?.addEventListener("click", hideAgentRunAlert);

byId("adminHeroCreateUser").addEventListener("click", () => {
  window.location.href = "/create-user.html";
});
byId("adminHeroListUser").addEventListener("click", async () => {
  window.location.href = "/list-user.html";
});
byId("adminHeroTicketList").addEventListener("click", async () => {
  window.location.href = "/list-ticket.html";
});

byId("refreshResolvedQueueBtn").addEventListener("click", loadAdminResolvedQueue);

byId("adminResolvedQueue").addEventListener("click", async (e) => {
  const btn = e.target.closest(".admin-close-ticket-btn");
  if (!btn) return;
  const ticketId = Number(btn.dataset.ticketId);
  btn.disabled = true;
  btn.textContent = "Closing...";
  const result = await request(`/admin/tickets/${ticketId}/close`, {
    method: "PATCH",
    headers: authHeaders(),
  });
  if (result.status >= 200 && result.status < 300) {
    showToast(`Ticket #${ticketId} closed`, "success");
    await loadAdminResolvedQueue();
    const statsRes = await request("/admin/stats", { headers: authHeaders() });
    renderAdminView("stats", statsRes);
  } else {
    btn.disabled = false;
    btn.textContent = "Close";
    showToast(`Failed to close ticket #${ticketId}`, "error");
  }
});

const logout = () => {
  stopAdminStatsAutoRefresh();
  accessToken = "";
  currentUser = null;
  currentLoginType = "general";
  currentRole = "guest";
  updateTokenView();
  setAuthState(false);
  clearSession();
  setResult("loginResult", "Token cleared.");
};

logoutTop.addEventListener("click", logout);

headerTabs.forEach((btn) => {
  btn.addEventListener("click", () => switchSection(btn.dataset.section));
});

byId("profileForm").addEventListener("submit", (e) => {
  e.preventDefault();
  localStorage.setItem("profile_name", byId("profileName").value.trim());
  setResult("profileResult", "Profile saved locally.");
  hydrateUserInfo();
});

byId("settingsForm").addEventListener("submit", (e) => {
  e.preventDefault();
  localStorage.setItem("setting_theme", byId("settingTheme").value);
  localStorage.setItem("setting_notify", byId("settingNotify").checked ? "1" : "0");
  localStorage.setItem("setting_compact", byId("settingCompact").checked ? "1" : "0");
  applySettings();
  setResult("settingsResult", "Settings saved.");
});

byId("settingTheme")?.addEventListener("change", syncThemeHint);

byId("employeeAssignedTicketsBtn")?.addEventListener("click", () => {
  window.location.href = "/my-assigned-tickets.html";
});

updateTokenView();
applySettings();
applyRoleUI();
const restored = restoreSession();
if (!restored) {
  setAuthState(false);
  stopAdminStatsAutoRefresh();
} else {
  startAdminStatsAutoRefresh();
}
switchSection(localStorage.getItem("active_section") || "overviewSection");

const ticketWorkParam = new URLSearchParams(window.location.search).get("ticketWork");
if (ticketWorkParam && restored) {
  const tid = Number(ticketWorkParam);
  if (tid > 0) {
    byId("workTicketId").value = String(tid);
    byId("conversationTicketId").value = String(tid);
    switchSection("ticketSection");
    void loadTicketDocsForWork(tid);
    showToast(`Ticket #${tid} loaded for work`, "success");
  }
  window.history.replaceState({}, document.title, window.location.pathname);
}
