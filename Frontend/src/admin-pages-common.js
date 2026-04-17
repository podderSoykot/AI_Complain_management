export const API_BASE = "http://127.0.0.1:8000/api/v1";
export const SESSION_KEY = "acm_session";

export function getSession() {
  const raw = localStorage.getItem(SESSION_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function authHeaders() {
  const session = getSession();
  if (!session?.token) return { "Content-Type": "application/json" };
  return {
    Authorization: `Bearer ${session.token}`,
    "Content-Type": "application/json",
  };
}

export async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, options);
  const data = await res.json().catch(() => ({}));
  return { status: res.status, data };
}

export function goDashboard() {
  window.location.href = "/";
}
