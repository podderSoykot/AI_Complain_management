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
    <section class="card table-wrap">
      <table id="userTable">
        <thead><tr><th>ID</th><th>Name</th><th>Email</th><th>Role</th><th>Tenant</th><th>Status</th></tr></thead>
        <tbody><tr><td colspan="6">Loading...</td></tr></tbody>
      </table>
    </section>
  </div>
`;

document.querySelector("#backBtn").addEventListener("click", goDashboard);

const session = getSession();
const tbody = document.querySelector("#userTable tbody");

const load = async () => {
  if (!session?.token || session?.role !== "admin") {
    tbody.innerHTML = `<tr><td colspan="6">Unauthorized. Please login as admin first.</td></tr>`;
    return;
  }
  const res = await request("/admin/users", { headers: authHeaders() });
  if (res.status < 200 || res.status >= 300 || !Array.isArray(res.data)) {
    tbody.innerHTML = `<tr><td colspan="6">Failed to load data: ${res.status}</td></tr>`;
    return;
  }
  tbody.innerHTML = res.data
    .slice(0, 100)
    .map(
      (u) =>
        `<tr><td>${u.id}</td><td>${u.full_name ?? "-"}</td><td>${u.email ?? "-"}</td><td>${u.role ?? "-"}</td><td>${u.tenant_id ?? "-"}</td><td>${u.is_active === 1 ? "Active" : "Inactive"}</td></tr>`
    )
    .join("");
};

document.querySelector("#refreshBtn").addEventListener("click", load);
load();
