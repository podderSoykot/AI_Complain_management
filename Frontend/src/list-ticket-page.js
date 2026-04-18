import "./admin-pages.css";
import {
  authHeaders,
  getSession,
  goDashboard,
  previewTicketAttachment,
  request,
} from "./admin-pages-common";

const app = document.querySelector("#app");

app.innerHTML = `
  <div class="container">
    <div class="top">
      <div class="title">
        <h1>Ticket List</h1>
        <p>Admin operation</p>
      </div>
      <div class="actions">
        <button id="refreshBtn" class="btn btn-primary">Refresh</button>
        <button id="backBtn" class="btn btn-ghost">Back</button>
      </div>
    </div>
    <section class="card table-wrap">
      <h3>Need Assignment</h3>
      <p class="muted">These tickets are not assigned yet. Assign from here.</p>
      <table id="pendingTicketTable">
        <thead><tr><th>ID</th><th>Title</th><th>Category</th><th>Priority</th><th>Status</th><th>Files</th><th>Assign</th></tr></thead>
        <tbody><tr><td colspan="8">Loading...</td></tr></tbody>
      </table>
    </section>
    <section class="card table-wrap">
      <h3>Assigned In Progress</h3>
      <p class="muted">Who is assigned, current status, and ongoing work.</p>
      <table id="assignedTicketTable">
        <thead><tr><th>ID</th><th>Title</th><th>Category</th><th>Priority</th><th>Status</th><th>Files</th><th>Assigned To</th></tr></thead>
        <tbody><tr><td colspan="7">Loading...</td></tr></tbody>
      </table>
    </section>
    <section class="card table-wrap">
      <h3>Resolved by employee — waiting for close</h3>
      <p class="muted">Only tickets marked <strong>resolved</strong> by the assigned support/supervisor appear here. Admin closes after review.</p>
      <table id="resolvedTicketTable">
        <thead><tr><th>ID</th><th>Title</th><th>Priority</th><th>Resolved by (employee)</th><th>Status</th><th>Files</th><th>Action</th></tr></thead>
        <tbody><tr><td colspan="7">Loading...</td></tr></tbody>
      </table>
    </section>
    <div id="assignModal" class="modal hidden">
      <div class="modal-card">
        <div class="modal-head">
          <h3>Assign Ticket</h3>
          <button id="closeAssignModal" class="btn btn-ghost">Close</button>
        </div>
        <p id="assignTicketMeta" class="muted">Ticket: -</p>
        <div class="routing-hint">
          <strong>AI routing help</strong>
          <p class="muted routing-hint-lead">Complaint is scanned (NLP-style keywords). Staff are ranked by <strong>department fit</strong> then workload so the right team resolves it fastest.</p>
          <pre id="routingHint" class="routing-hint-pre">Loading…</pre>
        </div>
        <form id="assignForm" class="grid">
          <label>Assign To (Support Agent / Supervisor)
            <select id="assigneeSelect" required></select>
          </label>
          <button type="submit" class="btn btn-primary">Assign Ticket</button>
        </form>
        <div id="assignResult" class="result"></div>
      </div>
    </div>
    <div id="filesModal" class="modal hidden">
      <div class="modal-card">
        <div class="modal-head">
          <h3>Supporting documents</h3>
          <button type="button" id="closeFilesModal" class="btn btn-ghost">Close</button>
        </div>
        <p id="filesModalMeta" class="muted">Ticket #—</p>
        <p class="muted" style="margin-top:0;font-size:0.85rem;">Use View to open PDF, images, or text in the page.</p>
        <ul id="filesModalList" class="ticket-docs-list"></ul>
      </div>
    </div>
  </div>
`;

document.querySelector("#backBtn").addEventListener("click", goDashboard);

const session = getSession();
const pendingTbody = document.querySelector("#pendingTicketTable tbody");
const assignedTbody = document.querySelector("#assignedTicketTable tbody");
const resolvedTbody = document.querySelector("#resolvedTicketTable tbody");
const assignModal = document.querySelector("#assignModal");
const assignForm = document.querySelector("#assignForm");
const assigneeSelect = document.querySelector("#assigneeSelect");
const assignTicketMeta = document.querySelector("#assignTicketMeta");
const routingHint = document.querySelector("#routingHint");
const assignResult = document.querySelector("#assignResult");
let ticketsCache = [];
let employeeOptions = [];
let employeeMap = new Map();
let selectedTicketId = null;

const setAssignResult = (data) => {
  assignResult.textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
};

const closeAssignModal = () => {
  assignModal.classList.add("hidden");
  selectedTicketId = null;
  setAssignResult("");
  routingHint.textContent = "";
};

const fillAssigneeOptions = () => {
  if (!employeeOptions.length) {
    assigneeSelect.innerHTML = `<option value="">No support user found</option>`;
    return;
  }
  assigneeSelect.innerHTML = employeeOptions
    .map(
      (u) =>
        `<option value="${u.id}">${u.full_name || u.email} — ${(u.department || "").trim() || "no dept"} (${u.role})</option>`
    )
    .join("");
};

const loadRoutingSuggestion = async (ticketId) => {
  routingHint.textContent = "Loading suggestion…";
  const res = await request(`/admin/tickets/${ticketId}/routing-suggestion`, { headers: authHeaders() });
  if (res.status < 200 || res.status >= 300 || !res.data) {
    routingHint.textContent = `Could not load routing hint (HTTP ${res.status}).`;
    return;
  }
  const d = res.data;
  const top = Array.isArray(d.candidates) ? d.candidates.slice(0, 8) : [];
  const lines = [
    `Detected complaint theme: ${d.nlp_category}`,
    "",
    d.admin_guidance || "",
    "",
    "Ranked staff (department match → fewer active tickets):",
    ...top.map(
      (c, i) =>
        `${i + 1}. #${c.user_id} ${c.full_name || c.email} | dept: ${c.department || "—"} | match ${c.department_match_score} | active tickets ${c.active_tickets}`
    ),
  ];
  if (d.recommended_user_id != null) {
    lines.push("", `Suggested assignee: user #${d.recommended_user_id} (pre-selected below).`);
    assigneeSelect.value = String(d.recommended_user_id);
  } else {
    lines.push("", "No active support staff found.");
  }
  routingHint.textContent = lines.join("\n");
};

const openAssignModal = async (ticketId) => {
  const ticket = ticketsCache.find((t) => t.id === ticketId);
  if (!ticket) return;
  selectedTicketId = ticket.id;
  assignTicketMeta.textContent = `Ticket #${ticket.id} — ${ticket.title || "-"}`;
  fillAssigneeOptions();
  assigneeSelect.value = "";
  setAssignResult("");
  routingHint.textContent = "Loading suggestion…";
  assignModal.classList.remove("hidden");
  await loadRoutingSuggestion(ticketId);
};

const loadAssignableEmployees = async () => {
  const usersRes = await request("/admin/users?limit=500", { headers: authHeaders() });
  if (usersRes.status >= 200 && usersRes.status < 300 && Array.isArray(usersRes.data)) {
    employeeOptions = usersRes.data.filter((u) => u.is_active === 1 && (u.role === "support_agent" || u.role === "supervisor"));
    employeeMap = new Map(usersRes.data.map((u) => [u.id, u]));
  } else {
    employeeOptions = [];
    employeeMap = new Map();
  }
};

const assigneeLabel = (assigneeId, ticket = null) => {
  if (!assigneeId) return "—";
  const nameFromApi = ticket && (ticket.assignee_full_name || "").trim();
  const deptFromApi = ticket && (ticket.assignee_department || "").trim();
  if (nameFromApi) {
    return deptFromApi ? `${nameFromApi} (${deptFromApi})` : nameFromApi;
  }
  const u = employeeMap.get(assigneeId);
  if (!u) return `User #${assigneeId}`;
  const d = (u.department || "").trim();
  return d ? `${u.full_name || u.email} — ${d} (${u.role})` : `${u.full_name || u.email} (${u.role})`;
};

const statusBadge = (status) => {
  const safe = status || "unknown";
  return `<span class="status-badge status-${safe}">${safe}</span>`;
};

const escapeHtml = (s) =>
  String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

const attachmentCell = (t) => {
  const n = Number(t.attachment_count ?? 0);
  if (!n) return `<span class="muted">0</span>`;
  return `<button type="button" class="btn btn-ghost btn-sm ticket-files-btn" data-ticket-id="${t.id}">View (${n})</button>`;
};

const filesModal = document.querySelector("#filesModal");
const filesModalList = document.querySelector("#filesModalList");
const filesModalMeta = document.querySelector("#filesModalMeta");

const closeFilesModal = () => {
  filesModal?.classList.add("hidden");
  if (filesModalList) filesModalList.innerHTML = "";
};

const openFilesModal = async (ticketId) => {
  if (!filesModal || !filesModalList || !filesModalMeta) return;
  filesModalMeta.textContent = `Ticket #${ticketId}`;
  filesModalList.innerHTML = `<li class="muted">Loading…</li>`;
  filesModal.classList.remove("hidden");
  const res = await request(`/tickets/${ticketId}`, { headers: authHeaders() });
  if (res.status < 200 || res.status >= 300) {
    filesModalList.innerHTML = `<li class="muted">Could not load (HTTP ${res.status}).</li>`;
    return;
  }
  const atts = Array.isArray(res.data?.attachments) ? res.data.attachments : [];
  if (!atts.length) {
    filesModalList.innerHTML = `<li class="muted">No supporting documents for this ticket.</li>`;
    return;
  }
  filesModalList.innerHTML = atts
    .map(
      (a) =>
        `<li><span class="ticket-attachment-filename">${escapeHtml(a.original_filename)}</span> <span class="muted">(${(a.size_bytes / 1024).toFixed(1)} KB)</span> <button type="button" class="btn btn-secondary btn-sm ticket-files-preview" data-tid="${ticketId}" data-aid="${a.id}" data-fn="${encodeURIComponent(a.original_filename)}" data-ct="${encodeURIComponent(a.content_type || "")}">View</button></li>`,
    )
    .join("");
};

const load = async () => {
  if (!session?.token || session?.role !== "admin") {
    pendingTbody.innerHTML = `<tr><td colspan="8">Unauthorized. Please login as admin first.</td></tr>`;
    assignedTbody.innerHTML = `<tr><td colspan="7">Unauthorized. Please login as admin first.</td></tr>`;
    resolvedTbody.innerHTML = `<tr><td colspan="7">Unauthorized. Please login as admin first.</td></tr>`;
    return;
  }
  await loadAssignableEmployees();
  const res = await request("/admin/tickets?limit=500", { headers: authHeaders() });
  if (res.status < 200 || res.status >= 300 || !Array.isArray(res.data)) {
    pendingTbody.innerHTML = `<tr><td colspan="8">Failed to load data: ${res.status}</td></tr>`;
    assignedTbody.innerHTML = `<tr><td colspan="7">Failed to load data: ${res.status}</td></tr>`;
    resolvedTbody.innerHTML = `<tr><td colspan="7">Failed to load data: ${res.status}</td></tr>`;
    return;
  }
  ticketsCache = res.data.slice(0, 200);
  const pendingTickets = ticketsCache.filter((t) => !t.assignee_id);
  const resolvedTickets = ticketsCache.filter((t) => t.assignee_id && t.status === "resolved");
  const assignedTickets = ticketsCache.filter((t) => !!t.assignee_id && t.status !== "resolved" && t.status !== "closed");

  pendingTbody.innerHTML = pendingTickets
    .slice(0, 100)
    .map(
      (t) =>
        `<tr class="ticket-row" data-ticket-id="${t.id}">
          <td>${t.id}</td>
          <td>${t.title ?? "-"}</td>
          <td>${t.category ?? "-"}</td>
          <td>${t.priority ?? "-"}</td>
          <td>${statusBadge(t.status)}</td>
          <td>${attachmentCell(t)}</td>
          <td><button class="btn btn-primary btn-assign" data-ticket-id="${t.id}">Assign</button></td>
        </tr>`
    )
    .join("") || `<tr><td colspan="8">No pending tickets for assignment.</td></tr>`;

  assignedTbody.innerHTML = assignedTickets
    .slice(0, 100)
    .map(
      (t) =>
        `<tr>
          <td>${t.id}</td>
          <td>${t.title ?? "-"}</td>
          <td>${t.category ?? "-"}</td>
          <td>${t.priority ?? "-"}</td>
          <td>${statusBadge(t.status)}</td>
          <td>${attachmentCell(t)}</td>
          <td>${assigneeLabel(t.assignee_id, t)}</td>
        </tr>`
    )
    .join("") || `<tr><td colspan="7">No assigned tickets yet.</td></tr>`;

  resolvedTbody.innerHTML = resolvedTickets
    .slice(0, 100)
    .map(
      (t) => `
        <tr>
          <td>${t.id}</td>
          <td>${t.title ?? "-"}</td>
          <td>${t.priority ?? "-"}</td>
          <td>${assigneeLabel(t.assignee_id, t)}</td>
          <td>${statusBadge(t.status)}</td>
          <td>${attachmentCell(t)}</td>
          <td><button class="btn btn-primary btn-close" data-ticket-id="${t.id}">Close Ticket</button></td>
        </tr>`
    )
    .join("") || `<tr><td colspan="7">No employee-resolved tickets waiting for close.</td></tr>`;
};

pendingTbody.addEventListener("click", (e) => {
  const assignBtn = e.target.closest(".btn-assign");
  if (!assignBtn) return;
  e.stopPropagation();
  const ticketId = Number(assignBtn.dataset.ticketId);
  void openAssignModal(ticketId);
});

resolvedTbody.addEventListener("click", async (e) => {
  const closeBtn = e.target.closest(".btn-close");
  if (!closeBtn) return;
  const ticketId = Number(closeBtn.dataset.ticketId);
  closeBtn.disabled = true;
  closeBtn.textContent = "Closing...";
  const res = await request(`/admin/tickets/${ticketId}/close`, {
    method: "PATCH",
    headers: authHeaders(),
  });
  if (res.status >= 200 && res.status < 300) {
    await load();
  } else {
    closeBtn.disabled = false;
    closeBtn.textContent = "Close Ticket";
    alert(`Failed to close ticket #${ticketId} (${res.status})`);
  }
});

assignForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!selectedTicketId) return;
  const assignee_user_id = Number(assigneeSelect.value);
  const res = await request(`/admin/tickets/${selectedTicketId}/assign`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ assignee_user_id }),
  });
  setAssignResult(res);
  if (res.status >= 200 && res.status < 300) {
    await load();
  }
});

document.querySelector("#closeAssignModal").addEventListener("click", closeAssignModal);
assignModal.addEventListener("click", (e) => {
  if (e.target === assignModal) closeAssignModal();
});

document.querySelector("#refreshBtn").addEventListener("click", load);

app.addEventListener("click", async (e) => {
  const viewFiles = e.target.closest(".ticket-files-btn");
  if (viewFiles) {
    e.stopPropagation();
    await openFilesModal(Number(viewFiles.dataset.ticketId));
  }
});

filesModalList?.addEventListener("click", async (e) => {
  const btn = e.target.closest(".ticket-files-preview");
  if (!btn) return;
  const tid = Number(btn.dataset.tid);
  const aid = Number(btn.dataset.aid);
  const fn = decodeURIComponent(btn.dataset.fn || "file");
  const ct = decodeURIComponent(btn.dataset.ct || "");
  try {
    await previewTicketAttachment(tid, aid, { original_filename: fn, content_type: ct });
  } catch (err) {
    alert(err?.message || "Could not open file");
  }
});

document.querySelector("#closeFilesModal")?.addEventListener("click", closeFilesModal);
filesModal?.addEventListener("click", (e) => {
  if (e.target === filesModal) closeFilesModal();
});

load();
