/**
 * Smart Doctor Connect AI — Shared Utilities (app.js)
 * Common functions used across all frontend pages:
 * - API base URL configuration
 * - XSS escaping
 * - Toast notifications
 * - Doctor card rendering (Cyber Dark Theme)
 * - Date/time utilities
 */

const API_BASE = "/api";

// ── XSS Escape Helper ──────────────────────────────────────────────────────
function esc(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ── Toast Notification ──────────────────────────────────────────────────────
function showToast(msg, duration = 3500) {
  let toast = document.getElementById("toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "toast";
    document.body.appendChild(toast);
  }
  toast.style.cssText = "position:fixed;bottom:1.5rem;left:50%;transform:translateX(-50%);z-index:300;background:rgba(11,15,25,0.92);border:1px solid rgba(0,242,254,0.2);color:#f1f5f9;font-size:0.75rem;font-weight:700;padding:0.85rem 1.5rem;border-radius:999px;backdrop-filter:blur(12px);box-shadow:0 8px 32px rgba(0,0,0,0.25);display:flex;align-items:center;gap:0.5rem;transition:all 0.3s cubic-bezier(0.4,0,0.2,1);";
  
  toast.textContent = msg;
  toast.classList.remove("hidden");
  toast.style.opacity = "1";
  toast.style.transform = "translateX(-50%) translateY(0)";
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(-50%) translateY(20px)";
    setTimeout(() => toast.classList.add("hidden"), 300);
  }, duration);
}

// ── Build Doctor Card HTML (Design System) ──────────────────────────────────
function buildDoctorCard(doc, options = {}) {
  const score = doc.match_score ?? 0;
  const scoreClass = score >= 70 ? "score-bar-fill--high" : score >= 40 ? "score-bar-fill--mid" : "score-bar-fill--low";
    
  const availBadge = doc.is_available
    ? '<span class="badge badge--teal">Available</span>'
    : '<span class="badge badge--coral">Offline</span>';

  const stars =
    "★".repeat(Math.round(doc.rating || 0)) +
    "☆".repeat(5 - Math.round(doc.rating || 0));

  const docId = doc._id || doc.id || "";
  const showScore = options.showScore !== false;
  const showBookBtn = options.showBookBtn !== false;

  window.doctorCache = window.doctorCache || {};
  window.doctorCache[docId] = doc.availability || {};

  let ctaHtml = "";
  if (showBookBtn) {
    ctaHtml = `
      <div style="display:flex;gap:0.5rem;margin-top:auto;padding-top:0.5rem;">
        <button onclick="openBooking('${esc(docId)}','${esc(doc.name)}', window.doctorCache['${esc(docId)}'])"
          class="btn btn-primary flex-1"
          ${doc.is_available ? '' : 'disabled style="opacity:0.4;cursor:not-allowed;"'}>Book Slot</button>
        <a href="/doctor-profile.html?id=${esc(docId)}"
          class="btn btn-ghost" style="font-size:0.7rem;">Profile</a>
      </div>`;
  }

  let scoreHtml = "";
  if (showScore) {
    scoreHtml = `
      <div style="margin-top:0.25rem;">
        <div style="display:flex;justify-content:space-between;margin-bottom:0.35rem;">
          <span class="label-micro">Clinical Fit</span>
          <span class="label-micro" style="color:var(--accent-cyan);">${score}%</span>
        </div>
        <div class="score-bar-track">
          <div class="score-bar-fill ${scoreClass}" style="width:${score}%"></div>
        </div>
      </div>`;
  }

  return `
    <div class="tech-card" style="padding:1.25rem;display:flex;flex-direction:column;gap:0.75rem;">
      <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:0.5rem;padding-bottom:0.75rem;border-bottom:1px solid var(--border-subtle);">
        <div style="width:48px;height:48px;border-radius:16px;background:rgba(0,242,254,0.06);border:1px solid rgba(0,242,254,0.15);display:flex;align-items:center;justify-content:center;font-size:1.5rem;flex-shrink:0;">👨‍⚕️</div>
        <div style="flex:1;min-width:0;">
          <h3 style="font-family:var(--font-display);font-weight:800;color:white;font-size:0.95rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${esc(doc.name)}</h3>
          <p style="color:var(--accent-cyan);font-size:0.65rem;font-weight:800;text-transform:uppercase;letter-spacing:0.08em;margin-top:2px;">${esc(doc.specialization)}</p>
        </div>
        ${availBadge}
      </div>
      <div style="display:flex;flex-wrap:wrap;gap:0.75rem;font-size:0.7rem;color:var(--text-muted);font-weight:600;">
        <span>📍 ${esc(doc.location)}</span>
        <span>🏥 ${esc(doc.consultation_type)}</span>
        <span>💰 Rs. ${doc.consultation_fee?.toLocaleString() ?? "—"}</span>
        <span>🎓 ${doc.experience_years} yrs</span>
      </div>
      <div style="display:flex;align-items:center;gap:0.5rem;font-size:0.75rem;background:var(--bg-input);padding:0.5rem 0.75rem;border-radius:var(--radius-sm);border:1px solid var(--border-subtle);">
        <span style="color:#FBBF24;">${stars}</span>
        <span style="color:var(--text-muted);font-weight:700;">${doc.rating?.toFixed(1) ?? "N/A"} (${doc.total_reviews} reviews)</span>
      </div>
      ${scoreHtml}
      ${ctaHtml}
    </div>`;
}

// ── Date Utilities ──────────────────────────────────────────────────────────
function getDayName(dateStr) {
  return new Date(dateStr + "T00:00:00").toLocaleDateString("en-US", {
    weekday: "long",
  });
}

function getTodayStr() {
  return new Date().toISOString().split("T")[0];
}

// ── Fetch Helper ────────────────────────────────────────────────────────────
async function apiFetch(url, options = {}) {
  const resp = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw { status: resp.status, detail: err.detail || "Request failed" };
  }
  return resp.json();
}
