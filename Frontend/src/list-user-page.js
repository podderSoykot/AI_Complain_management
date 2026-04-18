import "./admin-pages.css";
import { authHeaders, getSession, goDashboard, request } from "./admin-pages-common";

const app = document.querySelector("#app");

app.innerHTML = `
  <div class="container">
    <div class="top">
      <div class="title">
        <h1>User List</h1>
        <p>Admin operation</p>
      </div>
      <div class="actions">
        <button id="refreshBtn" class="btn btn-primary">Refresh</button>
        <button id="backBtn" class="btn btn-ghost">Back</button>
      </div>
    </div>
    <div id="userListsRoot">
      <section class="card table-wrap">
        <h2 class="section-title">Company staff</h2>
        <p class="section-desc muted">People who work on the platform: admins, supervisors, and support agents.</p>
        <table id="staffUserTable">
          <thead><tr><th>ID</th><th>Name</th><th>Email</th><th>Role</th><th>Department</th><th>Tenant</th><th>Status</th><th>Actions</th></tr></thead>
          <tbody id="staffUserTbody"><tr><td colspan="8">Loading...</td></tr></tbody>
        </table>
      </section>
      <section class="card table-wrap">
        <h2 class="section-title">Customers</h2>
        <p class="section-desc muted">End users who use the service and submit complaints.</p>
        <table id="customerUserTable">
          <thead><tr><th>ID</th><th>Name</th><th>Email</th><th>Role</th><th>Department</th><th>Tenant</th><th>Status</th><th>Actions</th></tr></thead>
          <tbody id="customerUserTbody"><tr><td colspan="8">Loading...</td></tr></tbody>
        </table>
      </section>
    </div>
    <div id="editUserModal" class="modal hidden">
      <div class="modal-card">
        <div class="modal-head">
          <h3>Edit User</h3>
          <button type="button" id="closeEditUserModal" class="btn btn-ghost">Close</button>
        </div>
        <p id="editUserMeta" class="muted">User #</p>
        <form id="editUserForm" class="grid">
          <label>Full name
            <input id="editFullName" name="full_name" type="text" required minlength="2" maxlength="120" />
          </label>
          <label>Email
            <input id="editEmail" name="email" type="email" required />
          </label>
          <label>Role
            <select id="editRole" name="role" required>
              <option value="customer">customer</option>
              <option value="support_agent">support_agent</option>
              <option value="supervisor">supervisor</option>
              <option value="admin">admin</option>
            </select>
          </label>
          <label>Department
            <span class="muted">(for Support Agent & Supervisor)</span>
            <input id="editDepartment" name="department" type="text" maxlength="80" placeholder="e.g. Billing" disabled />
          </label>
          <label>Status
            <select id="editActive" name="is_active" required>
              <option value="1">Active</option>
              <option value="0">Inactive</option>
            </select>
          </label>
          <button type="submit" class="btn btn-primary">Save changes</button>
        </form>
        <div id="editUserResult" class="result"></div>
      </div>
    </div>
  </div>
`;

document.querySelector("#backBtn").addEventListener("click", goDashboard);

const session = getSession();
const staffTbody = document.querySelector("#staffUserTbody");
const customerTbody = document.querySelector("#customerUserTbody");
const userListsRoot = document.querySelector("#userListsRoot");
const editUserModal = document.querySelector("#editUserModal");
const editUserForm = document.querySelector("#editUserForm");
const editUserMeta = document.querySelector("#editUserMeta");
const editUserResult = document.querySelector("#editUserResult");
const editFullName = document.querySelector("#editFullName");
const editEmail = document.querySelector("#editEmail");
const editRole = document.querySelector("#editRole");
const editDepartment = document.querySelector("#editDepartment");
const editActive = document.querySelector("#editActive");

let usersCache = [];
let editingUserId = null;

const STAFF_ROLES = new Set(["admin", "support_agent", "supervisor"]);

const isStaffUser = (u) => STAFF_ROLES.has(u.role);

const syncEditDepartmentField = () => {
  const isEmployee = editRole.value === "support_agent" || editRole.value === "supervisor";
  editDepartment.disabled = !isEmployee;
  editDepartment.required = isEmployee;
  if (!isEmployee) {
    editDepartment.value = "";
  }
};

editRole.addEventListener("change", syncEditDepartmentField);

const escapeHtml = (s) =>
  String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

const setEditResult = (msg) => {
  editUserResult.textContent = typeof msg === "string" ? msg : JSON.stringify(msg, null, 2);
};

const closeEditModal = () => {
  editUserModal.classList.add("hidden");
  editingUserId = null;
  setEditResult("");
};

const openEditModal = (userId) => {
  const u = usersCache.find((x) => x.id === userId);
  if (!u) return;
  editingUserId = userId;
  editUserMeta.textContent = `User #${u.id}`;
  editFullName.value = u.full_name ?? "";
  editEmail.value = u.email ?? "";
  editRole.value = u.role ?? "customer";
  editDepartment.value = u.department ?? "";
  editActive.value = String(u.is_active === 1 ? 1 : 0);
  syncEditDepartmentField();
  setEditResult("");
  editUserModal.classList.remove("hidden");
};

const renderUserRows = (list, sessionEmail) =>
  list
    .map((u) => {
      const isSelf = sessionEmail && String(u.email ?? "").toLowerCase() === String(sessionEmail).toLowerCase();
      const statusLabel = u.is_active === 1 ? "Active" : "Inactive";
      const deptLabel = u.department?.trim() ? u.department : "—";
      const deleteCell = isSelf
        ? `<span class="muted">—</span>`
        : `<button type="button" class="btn btn-danger btn-sm btn-delete-user" data-user-id="${u.id}">Delete</button>`;
      return `<tr>
        <td>${u.id}</td>
        <td>${escapeHtml(u.full_name ?? "-")}</td>
        <td>${escapeHtml(u.email ?? "-")}</td>
        <td>${escapeHtml(u.role ?? "-")}</td>
        <td>${escapeHtml(deptLabel)}</td>
        <td>${escapeHtml(u.tenant_id ?? "-")}</td>
        <td>${escapeHtml(statusLabel)}</td>
        <td class="user-actions">
          <button type="button" class="btn btn-ghost btn-sm btn-edit-user" data-user-id="${u.id}">Edit</button>
          ${deleteCell}
        </td>
      </tr>`;
    })
    .join("");

const emptyRow = (colspan, text) => `<tr><td colspan="${colspan}">${text}</td></tr>`;

const load = async () => {
  if (!session?.token || session?.role !== "admin") {
    const msg = emptyRow(8, "Unauthorized. Please login as admin first.");
    staffTbody.innerHTML = msg;
    customerTbody.innerHTML = msg;
    return;
  }
  const res = await request("/admin/users?limit=500", { headers: authHeaders() });
  if (res.status < 200 || res.status >= 300 || !Array.isArray(res.data)) {
    const msg = emptyRow(8, `Failed to load data: ${res.status}`);
    staffTbody.innerHTML = msg;
    customerTbody.innerHTML = msg;
    return;
  }
  usersCache = res.data.slice(0, 500);
  const staff = usersCache.filter(isStaffUser);
  const customers = usersCache.filter((u) => !isStaffUser(u));

  staffTbody.innerHTML =
    renderUserRows(staff, session?.email) || emptyRow(8, "No company staff in this list.");
  customerTbody.innerHTML =
    renderUserRows(customers, session?.email) || emptyRow(8, "No customers in this list.");
};

userListsRoot.addEventListener("click", async (e) => {
  const editBtn = e.target.closest(".btn-edit-user");
  if (editBtn) {
    openEditModal(Number(editBtn.dataset.userId));
    return;
  }
  const delBtn = e.target.closest(".btn-delete-user");
  if (!delBtn) return;
  const userId = Number(delBtn.dataset.userId);
  const u = usersCache.find((x) => x.id === userId);
  const label = u ? `${u.full_name || u.email} (#${userId})` : `#${userId}`;
  if (!confirm(`Delete user ${label}? This cannot be undone.`)) return;
  delBtn.disabled = true;
  const res = await request(`/admin/users/${userId}`, { method: "DELETE", headers: authHeaders() });
  delBtn.disabled = false;
  if (res.status >= 200 && res.status < 300) {
    await load();
    return;
  }
  const detail = res.data?.detail != null ? String(res.data.detail) : JSON.stringify(res.data);
  alert(`Delete failed (${res.status}): ${detail}`);
});

editUserForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!editingUserId) return;
  const role = editRole.value;
  const payload = {
    full_name: editFullName.value.trim(),
    email: editEmail.value.trim(),
    role,
    is_active: Number(editActive.value),
  };
  if (role === "support_agent" || role === "supervisor") {
    payload.department = editDepartment.value.trim();
  }
  const submitBtn = editUserForm.querySelector('button[type="submit"]');
  submitBtn.disabled = true;
  const res = await request(`/admin/users/${editingUserId}`, {
    method: "PATCH",
    headers: authHeaders(),
    body: JSON.stringify(payload),
  });
  submitBtn.disabled = false;
  if (res.status >= 200 && res.status < 300) {
    setEditResult("Saved.");
    await load();
    closeEditModal();
    return;
  }
  const detail = res.data?.detail != null ? String(res.data.detail) : JSON.stringify(res.data);
  setEditResult(`Error (${res.status}): ${detail}`);
});

document.querySelector("#closeEditUserModal").addEventListener("click", closeEditModal);
editUserModal.addEventListener("click", (e) => {
  if (e.target === editUserModal) closeEditModal();
});

document.querySelector("#refreshBtn").addEventListener("click", load);
load();
