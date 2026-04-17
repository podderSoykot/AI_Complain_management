import "./style.css";

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
      <div class="status-pill"><span class="dot"></span>API Ready</div>
      <button id="logoutTop" class="btn btn-danger btn-sm hidden">Logout</button>
    </div>
  </header>

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
        <div id="employeeProfilePanel" class="ticket-subpanel hidden">
          <div class="panel-head">
            <h3>My Assigned Tickets</h3>
            <button id="refreshMyTicketsBtn" class="btn btn-ghost">Refresh</button>
          </div>
          <p class="muted">Employee can see assigned tickets and work on them.</p>
          <div id="employeeTicketsResult" class="result large">No data yet.</div>
        </div>
      </section>

      <section id="settingsSection" class="content-section card hidden">
        <h2>Settings</h2>
        <p class="muted">Personal dashboard preferences.</p>
        <form id="settingsForm" class="form-grid">
          <label>Theme
            <select id="settingTheme">
              <option value="dark">Dark</option>
              <option value="midnight">Midnight</option>
            </select>
          </label>
          <label>
            <input id="settingNotify" type="checkbox" />
            Enable notification preview
          </label>
          <label>
            <input id="settingCompact" type="checkbox" />
            Compact card spacing
          </label>
          <button type="submit" class="btn btn-secondary">Save Settings</button>
        </form>
        <div id="settingsResult" class="result"></div>
      </section>

      <section id="ticketSection" class="content-section card hidden">
        <h2>Ticket Operations</h2>
        <p class="muted">Create and submit complaint tickets.</p>
        <div>
          <h3>Create Ticket</h3>
          <form id="ticketForm" class="form-grid">
            <label>Title<input id="ticketTitle" type="text" required /></label>
            <label>Description<textarea id="ticketDescription" rows="4" required></textarea></label>
            <button type="submit" class="btn btn-primary">Submit Ticket</button>
          </form>
          <div id="ticketResult" class="result"></div>
        </div>
        <div id="employeeTools" class="ticket-subpanel hidden">
          <h3>Support Workflow</h3>
          <p class="muted">For support agent/supervisor: move ticket through in-review, in-progress, and resolved.</p>
          <form id="ticketWorkStatusForm" class="form-grid">
            <label>Ticket ID<input id="workTicketId" type="number" min="1" required /></label>
            <label>Work Status
              <select id="workStatus" required>
                <option value="in_review">In Review</option>
                <option value="in_progress">In Progress</option>
                <option value="resolved">Resolved</option>
              </select>
            </label>
            <button type="submit" class="btn btn-secondary">Update Work Status</button>
          </form>
          <div id="workStatusResult" class="result"></div>
        </div>
        <div id="adminCloseTools" class="ticket-subpanel hidden">
          <h3>Admin Close Ticket</h3>
          <p class="muted">Admin can close a ticket after support marks it resolved.</p>
          <form id="adminCloseForm" class="form-grid">
            <label>Ticket ID<input id="adminCloseTicketId" type="number" min="1" required /></label>
            <button type="submit" class="btn btn-danger">Close Ticket</button>
          </form>
          <div id="adminCloseResult" class="result"></div>
        </div>
        <div class="ticket-subpanel">
          <h3>Ticket Conversation</h3>
          <p class="muted">Ask questions, request documents, reply, and track full issue conversation.</p>
          <form id="conversationForm" class="form-grid">
            <label>Ticket ID<input id="conversationTicketId" type="number" min="1" required /></label>
            <label>Message Type
              <select id="conversationType" required>
                <option value="note">Note</option>
                <option value="question">Question</option>
                <option value="document_request">Document Request</option>
                <option value="user_reply">User Reply</option>
                <option value="resolution_note">Resolution Note</option>
              </select>
            </label>
            <label>Message<textarea id="conversationMessage" rows="3" required></textarea></label>
            <button type="submit" class="btn btn-primary">Send Message</button>
          </form>
          <div class="conversation-actions">
            <button id="loadConversationBtn" class="btn btn-ghost">Load Conversation</button>
          </div>
          <div id="conversationResult" class="result large"></div>
        </div>
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
          <p class="muted">Resolved tickets assigned by support/supervisor. Admin can close from here.</p>
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
          <td>${u.tenant_id ?? "-"}</td>
          <td>${u.is_active === 1 ? "Active" : "Inactive"}</td>
        </tr>`
      )
      .join("");
    el.innerHTML = `
      <div class="admin-table-wrap">
        <table class="admin-table">
          <thead><tr><th>ID</th><th>Name</th><th>Email</th><th>Role</th><th>Tenant</th><th>Status</th></tr></thead>
          <tbody>${rows || `<tr><td colspan="6">No users found.</td></tr>`}</tbody>
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
const updateTokenView = () => {
  return;
};

const setAuthState = (isLoggedIn) => {
  authGate.classList.toggle("hidden", isLoggedIn);
  dashboard.classList.toggle("hidden", !isLoggedIn);
  logoutTop.classList.toggle("hidden", !isLoggedIn);
  roleBadge.classList.toggle("hidden", !isLoggedIn);
  headerNav.classList.toggle("hidden", !isLoggedIn);
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

const applySettings = () => {
  const compact = localStorage.getItem("setting_compact") === "1";
  document.body.classList.toggle("compact", compact);

  const theme = localStorage.getItem("setting_theme") || "dark";
  document.body.dataset.theme = theme;
  byId("settingTheme").value = theme;
  byId("settingNotify").checked = localStorage.getItem("setting_notify") === "1";
  byId("settingCompact").checked = compact;
};

const switchSection = (targetId) => {
  for (const id of sectionIds) {
    byId(id).classList.toggle("hidden", id !== targetId);
  }
  headerTabs.forEach((btn) => btn.classList.toggle("active", btn.dataset.section === targetId));
  localStorage.setItem("active_section", targetId);
};

const applyRoleUI = () => {
  const adminHeaderTabs = headerTabs.filter((btn) => btn.classList.contains("admin-only-tab"));
  const isAdmin = currentRole === "admin";
  adminHeaderTabs.forEach((btn) => btn.classList.toggle("hidden", !isAdmin));
  const employeeTools = byId("employeeTools");
  const adminCloseTools = byId("adminCloseTools");
  const employeeProfilePanel = byId("employeeProfilePanel");
  if (employeeTools) employeeTools.classList.toggle("hidden", currentLoginType !== "employee");
  if (employeeProfilePanel) employeeProfilePanel.classList.toggle("hidden", currentLoginType !== "employee");
  if (adminCloseTools) adminCloseTools.classList.toggle("hidden", !isAdmin);
  if (!isAdmin && byId("adminSection") && !byId("adminSection").classList.contains("hidden")) {
    switchSection("overviewSection");
  }
};

const renderConversation = (result) => {
  const el = byId("conversationResult");
  if (result.status < 200 || result.status >= 300) {
    setResult("conversationResult", result);
    return;
  }
  const messages = Array.isArray(result.data) ? result.data : [];
  if (!messages.length) {
    el.innerHTML = `<div class="conversation-empty">No conversation yet for this ticket.</div>`;
    return;
  }
  el.innerHTML = messages
    .map((msg) => {
      const createdAt = msg.created_at ? new Date(msg.created_at).toLocaleString() : "-";
      return `
        <div class="conversation-item">
          <div class="conversation-meta">
            <span class="pill">${msg.message_type || "note"}</span>
            <span>${msg.sender_role || "user"} #${msg.sender_user_id ?? "-"}</span>
            <span>${createdAt}</span>
          </div>
          <div class="conversation-text">${msg.message || ""}</div>
        </div>
      `;
    })
    .join("");
};

const renderEmployeeAssignedTickets = (result) => {
  const el = byId("employeeTicketsResult");
  if (!el) return;
  if (result.status < 200 || result.status >= 300) {
    setResult("employeeTicketsResult", result);
    return;
  }
  const tickets = Array.isArray(result.data) ? result.data : [];
  if (!tickets.length) {
    el.innerHTML = `<div class="conversation-empty">No tickets assigned to you yet.</div>`;
    return;
  }
  el.innerHTML = `
    <div class="admin-table-wrap">
      <table class="admin-table">
        <thead><tr><th>ID</th><th>Title</th><th>Status</th><th>Priority</th><th>Action</th></tr></thead>
        <tbody>
          ${tickets
            .map(
              (t) => `
                <tr>
                  <td>${t.id}</td>
                  <td>${t.title ?? "-"}</td>
                  <td><span class="pill">${t.status ?? "-"}</span></td>
                  <td>${t.priority ?? "-"}</td>
                  <td><button class="btn btn-secondary btn-sm ticket-work-btn" data-ticket-id="${t.id}">Work</button></td>
                </tr>
              `
            )
            .join("")}
        </tbody>
      </table>
    </div>
  `;
};

const loadEmployeeAssignedTickets = async () => {
  if (currentLoginType !== "employee") return;
  const result = await request("/tickets/assigned/me?limit=200", { headers: authHeaders() });
  renderEmployeeAssignedTickets(result);
};

const renderResolvedQueue = (result) => {
  const el = byId("adminResolvedQueue");
  if (!el) return;
  if (result.status < 200 || result.status >= 300 || !Array.isArray(result.data)) {
    setResult("adminResolvedQueue", result);
    return;
  }

  const resolved = result.data.filter((t) => t.status === "resolved");
  if (!resolved.length) {
    el.innerHTML = `<div class="conversation-empty">No resolved tickets waiting for close.</div>`;
    return;
  }

  const rows = resolved
    .slice(0, 100)
    .map(
      (t) => `
        <tr>
          <td>${t.id}</td>
          <td>${t.title ?? "-"}</td>
          <td>${t.priority ?? "-"}</td>
          <td>${t.assignee_id ?? "-"}</td>
          <td><span class="pill">resolved</span></td>
          <td><button class="btn btn-danger btn-sm admin-close-ticket-btn" data-ticket-id="${t.id}">Close</button></td>
        </tr>
      `
    )
    .join("");

  el.innerHTML = `
    <div class="admin-table-wrap">
      <table class="admin-table">
        <thead><tr><th>ID</th><th>Title</th><th>Priority</th><th>Assignee</th><th>Status</th><th>Action</th></tr></thead>
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
    currentRole = saved.role || "user";
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
    currentRole = type === "admin" ? "admin" : type === "employee" ? "employee" : "user";
    updateTokenView();
    hydrateUserInfo();
    applySettings();
    applyRoleUI();
    setAuthState(true);
    saveSession();
    startAdminStatsAutoRefresh();
    loadEmployeeAssignedTickets();
  }
  setResult("loginResult", result);
});

byId("ticketForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = {
    title: byId("ticketTitle").value.trim(),
    description: byId("ticketDescription").value.trim(),
  };
  const result = await request("/tickets", {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(payload),
  });
  byId("ticketResult").textContent = "";
  if (result.status >= 200 && result.status < 300) {
    const ticketId = result.data?.id;
    showToast(ticketId ? `Ticket created successfully (ID: ${ticketId})` : "Ticket created successfully", "success");
    byId("ticketForm").reset();
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
    setResult("conversationResult", result);
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

byId("refreshMyTicketsBtn").addEventListener("click", loadEmployeeAssignedTickets);

byId("employeeTicketsResult").addEventListener("click", (e) => {
  const btn = e.target.closest(".ticket-work-btn");
  if (!btn) return;
  const ticketId = Number(btn.dataset.ticketId);
  byId("workTicketId").value = ticketId;
  byId("conversationTicketId").value = ticketId;
  switchSection("ticketSection");
  showToast(`Ticket #${ticketId} ready for work`, "success");
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
  loadEmployeeAssignedTickets();
}
switchSection(localStorage.getItem("active_section") || "overviewSection");
