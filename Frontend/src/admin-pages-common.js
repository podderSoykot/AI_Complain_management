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

/** Bearer only (for multipart or binary fetch). */
export function authHeadersBearer() {
  const session = getSession();
  if (!session?.token) return {};
  return { Authorization: `Bearer ${session.token}` };
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function escapeAttr(s) {
  return escapeHtml(s).replace(/"/g, "&quot;");
}

let previewObjectUrl = null;
let previewModalEl = null;

function closeAttachmentPreview() {
  if (previewObjectUrl) {
    URL.revokeObjectURL(previewObjectUrl);
    previewObjectUrl = null;
  }
  if (previewModalEl) {
    previewModalEl.style.display = "none";
    const body = previewModalEl.querySelector("[data-acm-preview-body]");
    if (body) body.innerHTML = "";
  }
}

function ensurePreviewModal() {
  if (previewModalEl) return previewModalEl;
  const el = document.createElement("div");
  el.id = "acm-attachment-preview";
  el.style.cssText =
    "position:fixed;inset:0;z-index:10000;display:none;place-items:center;padding:16px;background:rgba(15,23,42,0.55);backdrop-filter:blur(6px);";
  el.innerHTML = `
    <div style="width:min(920px,96vw);max-height:92vh;overflow:auto;background:#fff;border:1px solid #e2e8f0;border-radius:14px;box-shadow:0 20px 50px rgba(0,0,0,0.2);padding:14px;">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:10px;">
        <h3 data-acm-preview-title style="margin:0;font-size:1.05rem;color:#0f172a;">Preview</h3>
        <button type="button" data-acm-preview-close class="btn btn-ghost" style="flex-shrink:0;">Close</button>
      </div>
      <div data-acm-preview-body style="min-height:120px;"></div>
    </div>
  `;
  el.addEventListener("click", (e) => {
    if (e.target === el) closeAttachmentPreview();
  });
  el.querySelector("[data-acm-preview-close]")?.addEventListener("click", closeAttachmentPreview);
  document.body.appendChild(el);
  previewModalEl = el;
  return el;
}

/**
 * Open PDF / image / text in a modal on the same page (no forced download).
 * @param {{ original_filename: string, content_type?: string }} meta
 */
export async function previewTicketAttachment(ticketId, attachmentId, meta) {
  const filename = meta?.original_filename || "file";
  const hintedType = (meta?.content_type || "").split(";")[0].trim();

  const modal = ensurePreviewModal();
  const titleEl = modal.querySelector("[data-acm-preview-title]");
  const body = modal.querySelector("[data-acm-preview-body]");
  if (!body || !titleEl) return;

  titleEl.textContent = filename;
  body.innerHTML = `<p style="margin:0;color:#64748b;font-size:0.9rem;">Loading…</p>`;
  modal.style.display = "grid";

  if (previewObjectUrl) {
    URL.revokeObjectURL(previewObjectUrl);
    previewObjectUrl = null;
  }

  const res = await fetch(`${API_BASE}/tickets/${ticketId}/attachments/${attachmentId}/download`, {
    headers: authHeadersBearer(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    body.innerHTML = `<p style="color:#b91c1c;">${escapeHtml(err.detail || `Could not load file (${res.status})`)}</p>`;
    return;
  }

  const blob = await res.blob();
  const lowerName = filename.toLowerCase();
  const rawType = (blob.type || hintedType || "").split(";")[0].trim().toLowerCase();
  const generic =
    !rawType || rawType === "application/octet-stream" || rawType === "binary/octet-stream";

  /** Photos: real image/* or common extensions (servers often send octet-stream). */
  const photoExt = /\.(jpe?g|png|gif|webp|bmp|svg|ico|avif|heic|heif)$/i.test(lowerName);
  const asImage = rawType.startsWith("image/") || (generic && photoExt);

  const asPdf = rawType === "application/pdf" || lowerName.endsWith(".pdf");

  /** Plain text and similar readable types; extension fallback when MIME is wrong. */
  const textExt = /\.(txt|text|md|markdown|csv|log|json|xml|html?|htm|css|js|ts|yaml|yml|ini|env|sh|bat|ps1)$/i.test(
    lowerName,
  );
  const asText =
    rawType.startsWith("text/") ||
    rawType === "application/json" ||
    rawType === "application/xml" ||
    rawType === "text/xml" ||
    (generic && textExt);

  previewObjectUrl = URL.createObjectURL(blob);

  if (asImage) {
    body.innerHTML = `<img src="${previewObjectUrl}" alt="${escapeAttr(filename)}" style="max-width:100%;height:auto;display:block;border-radius:8px;" />`;
  } else if (asPdf) {
    body.innerHTML = `<iframe src="${previewObjectUrl}" title="${escapeAttr(filename)}" style="width:100%;min-height:75vh;border:1px solid #e2e8f0;border-radius:8px;background:#f8fafc;"></iframe>`;
  } else if (asText) {
    const text = await blob.text();
    if (previewObjectUrl) {
      URL.revokeObjectURL(previewObjectUrl);
      previewObjectUrl = null;
    }
    body.innerHTML = `<pre style="margin:0;white-space:pre-wrap;word-break:break-word;max-height:75vh;overflow:auto;padding:12px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;font-size:0.82rem;color:#0f172a;">${escapeHtml(text)}</pre>`;
  } else {
    body.innerHTML = `
      <p style="color:#64748b;margin:0 0 10px;">This file type cannot be previewed here.</p>
      <p style="margin:0;"><a href="${previewObjectUrl}" target="_blank" rel="noopener">Open in new browser tab</a></p>
    `;
  }
}

/** Optional: save blob to device (same fetch as preview). */
export async function downloadTicketAttachmentFile(ticketId, attachmentId, filename) {
  const res = await fetch(`${API_BASE}/tickets/${ticketId}/attachments/${attachmentId}/download`, {
    headers: authHeadersBearer(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Download failed (${res.status})`);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename || `attachment-${attachmentId}`;
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, options);
  const data = await res.json().catch(() => ({}));
  return { status: res.status, data };
}

export function goDashboard() {
  window.location.href = "/";
}
