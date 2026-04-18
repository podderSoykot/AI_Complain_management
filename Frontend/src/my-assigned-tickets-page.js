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
        <h1>My assigned tickets</h1>
        <p>Support / supervisor queue</p>
      </div>
      <div class="actions">
        <button id="refreshBtn" class="btn btn-primary">Refresh</button>
        <button id="backBtn" class="btn btn-ghost">Back to dashboard</button>
      </div>
    </div>
    <div id="ticketTables" class="muted">Loading…</div>
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
const ticketTables = document.querySelector("#ticketTables");
const filesModal = document.querySelector("#filesModal");
const filesModalList = document.querySelector("#filesModalList");
const filesModalMeta = document.querySelector("#filesModalMeta");

const escapeHtml = (s) =>
  String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

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

const attachmentCell = (t) => {
  const n = Number(t.attachment_count ?? 0);
  if (!n) return `<span class="muted">0</span>`;
  return `<button type="button" class="btn btn-ghost btn-sm ticket-files-btn" data-ticket-id="${t.id}">View (${n})</button>`;
};

const renderTables = (result) => {
  if (result.status < 200 || result.status >= 300) {
    ticketTables.innerHTML = `<p class="muted">Failed to load (HTTP ${result.status}). ${JSON.stringify(result.data)}</p>`;
    return;
  }
  const tickets = Array.isArray(result.data) ? result.data : [];
  if (!tickets.length) {
    ticketTables.innerHTML = `<p class="muted">No tickets assigned to you yet.</p>`;
    return;
  }

  const active = tickets.filter((t) => t.status !== "closed");
  const history = tickets.filter((t) => t.status === "closed");

  const rowHtml = (t, { allowWork }) => {
    const workCell =
      allowWork && t.status !== "closed"
        ? `<button type="button" class="btn btn-secondary btn-sm ticket-work-btn" data-ticket-id="${t.id}">Work on dashboard</button>`
        : `<span class="muted">—</span>`;
    return `
      <tr>
        <td>${t.id}</td>
        <td>${t.title ?? "-"}</td>
        <td><span class="pill">${t.status ?? "-"}</span></td>
        <td>${t.priority ?? "-"}</td>
        <td>${t.category ?? "-"}</td>
        <td>${attachmentCell(t)}</td>
        <td>${workCell}</td>
      </tr>`;
  };

  const tableBlock = (title, rows, emptyMsg) => `
    <section class="card table-wrap">
      <h2 class="section-title">${title}</h2>
      <div class="admin-table-wrap">
        <table class="admin-table">
          <thead><tr><th>ID</th><th>Title</th><th>Status</th><th>Priority</th><th>Category</th><th>Files</th><th>Action</th></tr></thead>
          <tbody>
            ${rows || `<tr><td colspan="7">${emptyMsg}</td></tr>`}
          </tbody>
        </table>
      </div>
    </section>
  `;

  const activeRows = active.map((t) => rowHtml(t, { allowWork: true })).join("");
  const historyRows = history.map((t) => rowHtml(t, { allowWork: false })).join("");

  ticketTables.innerHTML = `
    ${tableBlock("Active / resolved (until admin closes)", activeRows, "No active tickets assigned.")}
    ${history.length ? tableBlock("Closed by admin (history)", historyRows, "") : ""}
  `;
};

const load = async () => {
  if (!session?.token || session?.role !== "employee") {
    ticketTables.innerHTML = `<p class="muted">Unauthorized. Log in with <strong>Employee</strong> on the dashboard first.</p>`;
    return;
  }
  const result = await request("/tickets/assigned/me?limit=200", { headers: authHeaders() });
  renderTables(result);
};

ticketTables.addEventListener("click", (e) => {
  const btn = e.target.closest(".ticket-work-btn");
  if (!btn) return;
  const ticketId = Number(btn.dataset.ticketId);
  window.location.href = `/?ticketWork=${ticketId}`;
});

ticketTables.addEventListener("click", async (e) => {
  const viewFiles = e.target.closest(".ticket-files-btn");
  if (!viewFiles) return;
  await openFilesModal(Number(viewFiles.dataset.ticketId));
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

document.querySelector("#refreshBtn").addEventListener("click", load);
load();
