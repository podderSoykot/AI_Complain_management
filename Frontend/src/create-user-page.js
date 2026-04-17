import "./admin-pages.css";
import { authHeaders, getSession, goDashboard, request } from "./admin-pages-common";

const app = document.querySelector("#app");

app.innerHTML = `
  <div class="container">
    <div class="top">
      <div class="title">
        <h1>Create User</h1>
        <p>Admin operation</p>
      </div>
      <div class="actions">
        <button id="backBtn" class="btn btn-ghost">Back</button>
      </div>
    </div>
    <section class="card">
      <form id="createUserForm" class="grid">
        <label>Full Name<input id="name" type="text" required /></label>
        <label>Email<input id="email" type="email" required /></label>
        <label>Password<input id="password" type="password" minlength="8" required /></label>
        <label>Role
          <select id="role">
            <option value="customer">Customer</option>
            <option value="support_agent">Support Agent</option>
            <option value="supervisor">Supervisor</option>
            <option value="admin">Admin</option>
          </select>
        </label>
        <button type="submit" class="btn btn-primary">Create User</button>
      </form>
      <div id="result" class="result"></div>
    </section>
  </div>
`;

document.querySelector("#backBtn").addEventListener("click", goDashboard);

const session = getSession();
if (!session?.token || session?.role !== "admin") {
  document.querySelector("#result").textContent = "Unauthorized. Please login as admin first.";
}

document.querySelector("#createUserForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = {
    full_name: document.querySelector("#name").value.trim(),
    email: document.querySelector("#email").value.trim(),
    password: document.querySelector("#password").value,
    role: document.querySelector("#role").value,
  };
  const res = await request("/users", {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(payload),
  });
  document.querySelector("#result").textContent = JSON.stringify(res, null, 2);
  if (res.status >= 200 && res.status < 300) {
    document.querySelector("#createUserForm").reset();
  }
});
