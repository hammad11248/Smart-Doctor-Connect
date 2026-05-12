/**
 * Smart Doctor Connect AI — Shared Utilities (app.js)
 * Common functions used across all frontend pages:
 * - API base URL configuration
 * - XSS escaping
 * - Toast notifications
 * - Doctor card rendering
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
    toast.className =
      "fixed bottom-6 left-1/2 -translate-x-1/2 z-50 bg-slate-800 text-white text-sm px-5 py-3 rounded-full shadow-lg transition-all";
    document.body.appendChild(toast);
  }
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

// ── Build Doctor Card HTML ──────────────────────────────────────────────────
function buildDoctorCard(doc, options = {}) {
  const score = doc.match_score ?? 0;
  const scoreColor =
    score >= 70 ? "bg-green-500" : score >= 40 ? "bg-yellow-400" : "bg-slate-300";
  const availBadge = doc.is_available
    ? '<span class="bg-green-100 text-green-700 text-xs font-semibold px-2 py-0.5 rounded-full">Available</span>'
    : '<span class="bg-red-100 text-red-600 text-xs font-semibold px-2 py-0.5 rounded-full">Unavailable</span>';

  const stars =
    "★".repeat(Math.round(doc.rating || 0)) +
    "☆".repeat(5 - Math.round(doc.rating || 0));

  const docId = doc._id || doc.id || "";
  const showScore = options.showScore !== false;
  const showBookBtn = options.showBookBtn !== false;

  let ctaHtml = "";
  if (showBookBtn) {
    const availability = JSON.stringify(doc.availability || {}).replace(/"/g, "&quot;");
    ctaHtml = `
      <div class="flex gap-2 mt-auto">
        <button onclick="openBooking('${esc(docId)}','${esc(doc.name)}',${JSON.stringify(doc.availability || {})})"
          class="flex-1 bg-sky-600 hover:bg-sky-700 text-white text-sm font-semibold py-2.5 rounded-xl transition-colors
                 ${doc.is_available ? '' : 'opacity-50 cursor-not-allowed'}"
          ${doc.is_available ? '' : 'disabled'}>Book</button>
        <a href="/doctor-profile.html?id=${esc(docId)}"
          class="px-4 py-2.5 border border-slate-200 rounded-xl text-sm text-slate-600 hover:border-sky-400 hover:text-sky-600 transition-colors">
          Profile
        </a>
      </div>`;
  }

  let scoreHtml = "";
  if (showScore) {
    scoreHtml = `
      <div>
        <div class="flex justify-between text-xs text-slate-400 mb-1">
          <span>AI Match</span><span class="font-semibold text-slate-600">${score}%</span>
        </div>
        <div class="h-2 bg-slate-100 rounded-full overflow-hidden">
          <div class="score-bar h-full ${scoreColor} rounded-full" style="width:${score}%"></div>
        </div>
      </div>`;
  }

  return `
    <div class="doctor-card bg-white rounded-2xl border border-slate-200 shadow-sm p-5 flex flex-col gap-3">
      <div class="flex items-start justify-between gap-2">
        <div class="w-12 h-12 rounded-full bg-sky-100 flex items-center justify-center text-2xl shrink-0">👨‍⚕️</div>
        <div class="flex-1 min-w-0">
          <h3 class="font-bold text-slate-800 truncate text-sm sm:text-base">${esc(doc.name)}</h3>
          <p class="text-sky-600 text-xs font-medium">${esc(doc.specialization)}</p>
        </div>
        ${availBadge}
      </div>
      <div class="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
        <span>📍 ${esc(doc.location)}</span>
        <span>🏥 ${esc(doc.consultation_type)}</span>
        <span>💰 Rs. ${doc.consultation_fee?.toLocaleString() ?? "—"}</span>
        <span>🎓 ${doc.experience_years} yrs exp.</span>
      </div>
      <div class="flex items-center gap-2 text-xs">
        <span class="text-yellow-400 tracking-tight">${stars}</span>
        <span class="text-slate-500">${doc.rating?.toFixed(1) ?? "N/A"} (${doc.total_reviews} reviews)</span>
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
