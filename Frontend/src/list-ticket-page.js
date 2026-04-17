import "./admin-pages.css";
import { authHeaders, getSession, goDashboard, request } from "./admin-pages-common";

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
        <thead><tr><th>ID</th><th>Title</th><th>Category</th><th>Priority</th><th>Status</th><th>Assign</th></tr></thead>
        <tbody><tr><td colspan="7">Loading...</td></tr></tbody>
      </table>
    </section>
    <section class="card table-wrap">
      <h3>Assigned In Progress</h3>
      <p class="muted">Who is assigned, current status, and ongoing work.</p>
      <table id="assignedTicketTable">
        <thead><tr><th>ID</th><th>Title</th><th>Category</th><th>Priority</th><th>Status</th><th>Assigned To</th></tr></thead>
        <tbody><tr><td colspan="6">Loading...</td></tr></tbody>
      </table>
    </section>
    <section class="card table-wrap">
      <h3>Resolved Waiting for Close</h3>
      <p class="muted">Resolved by support/supervisor. Admin can now close.</p>
      <table id="resolvedTicketTable">
        <thead><tr><th>ID</th><th>Title</th><th>Priority</th><th>Assigned To</th><th>Status</th><th>Action</th></tr></thead>
        <tbody><tr><td colspan="6">Loading...</td></tr></tbody>
      </table>
    </section>
    <div id="assignModal" class="modal hidden">
      <div class="modal-card">
        <div class="modal-head">
          <h3>Assign Ticket</h3>
          <button id="closeAssignModal" class="btn btn-ghost">Close</button>
        </div>
        <p id="assignTicketMeta" class="muted">Ticket: -</p>
        <form id="assignForm" class="grid">
          <label>Assign To (Support Agent / Supervisor)
            <select id="assigneeSelect" required></select>
          </label>
          <button type="submit" class="btn btn-primary">Assign Ticket</button>
        </form>
        <div id="assignResult" class="result"></div>
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
};

const fillAssigneeOptions = () => {
  if (!employeeOptions.length) {
    assigneeSelect.innerHTML = `<option value="">No support user found</option>`;
    return;
  }
  assigneeSelect.innerHTML = employeeOptions
    .map((u) => `<option value="${u.id}">${u.full_name || u.email} (${u.role})</option>`)
    .join("");
};

const openAssignModal = (ticketId) => {
  const ticket = ticketsCache.find((t) => t.id === ticketId);
  if (!ticket) return;
  selectedTicketId = ticket.id;
  assignTicketMeta.textContent = `Ticket #${ticket.id} - ${ticket.title || "-"}`;
  fillAssigneeOptions();
  setAssignResult("");
  assignModal.classList.remove("hidden");
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

const assigneeLabel = (assigneeId) => {
  if (!assigneeId) return "-";
  const u = employeeMap.get(assigneeId);
  if (!u) return `User #${assigneeId}`;
  return `${u.full_name || u.email} (${u.role})`;
};

const statusBadge = (status) => {
  const safe = status || "unknown";
  return `<span class="status-badge status-${safe}">${safe}</span>`;
};

const load = async () => {
  if (!session?.token || session?.role !== "admin") {
    pendingTbody.innerHTML = `<tr><td colspan="6">Unauthorized. Please login as admin first.</td></tr>`;
    assignedTbody.innerHTML = `<tr><td colspan="6">Unauthorized. Please login as admin first.</td></tr>`;
    resolvedTbody.innerHTML = `<tr><td colspan="6">Unauthorized. Please login as admin first.</td></tr>`;
    return;
  }
  await loadAssignableEmployees();
  const res = await request("/admin/tickets?limit=500", { headers: authHeaders() });
  if (res.status < 200 || res.status >= 300 || !Array.isArray(res.data)) {
    pendingTbody.innerHTML = `<tr><td colspan="6">Failed to load data: ${res.status}</td></tr>`;
    assignedTbody.innerHTML = `<tr><td colspan="6">Failed to load data: ${res.status}</td></tr>`;
    resolvedTbody.innerHTML = `<tr><td colspan="6">Failed to load data: ${res.status}</td></tr>`;
    return;
  }
  ticketsCache = res.data.slice(0, 200);
  const pendingTickets = ticketsCache.filter((t) => !t.assignee_id);
  const resolvedTickets = ticketsCache.filter((t) => !!t.assignee_id && t.status === "resolved");
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
          <td><button class="btn btn-primary btn-assign" data-ticket-id="${t.id}">Assign</button></td>
        </tr>`
    )
    .join("") || `<tr><td colspan="6">No pending tickets for assignment.</td></tr>`;

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
          <td>${assigneeLabel(t.assignee_id)}</td>
        </tr>`
    )
    .join("") || `<tr><td colspan="6">No assigned tickets yet.</td></tr>`;

  resolvedTbody.innerHTML = resolvedTickets
    .slice(0, 100)
    .map(
      (t) => `
        <tr>
          <td>${t.id}</td>
          <td>${t.title ?? "-"}</td>
          <td>${t.priority ?? "-"}</td>
          <td>${assigneeLabel(t.assignee_id)}</td>
          <td>${statusBadge(t.status)}</td>
          <td><button class="btn btn-primary btn-close" data-ticket-id="${t.id}">Close Ticket</button></td>
        </tr>`
    )
    .join("") || `<tr><td colspan="6">No resolved tickets waiting for close.</td></tr>`;
};

pendingTbody.addEventListener("click", (e) => {
  const assignBtn = e.target.closest(".btn-assign");
  if (!assignBtn) return;
  e.stopPropagation();
  const ticketId = Number(assignBtn.dataset.ticketId);
  openAssignModal(ticketId);
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
load();
