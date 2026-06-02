/**
 * Smart-Doctor-Connect-AI — Search Logic (search.js)
 * Handles AI-powered symptom search, result rendering, and analysis banner display.
 */

// ── Search State ────────────────────────────────────────────────────────────
let searchDebounceTimer = null;

// ── Fill Search Input & Trigger ─────────────────────────────────────────────
function fillSearch(text) {
  const input = document.getElementById("searchInput");
  if (input) {
    input.value = text;
    handleSearch();
  }
}

// ── Main Search Handler ─────────────────────────────────────────────────────
async function handleSearch() {
  const input = document.getElementById("searchInput");
  if (!input) return;

  const q = input.value.trim();
  if (q.length < 3) {
    showToast("Please describe your symptoms (at least 3 characters).");
    return;
  }

  showSkeleton(true);
  hideAnalysisBanner();

  try {
    const resp = await fetch(
      `${API_BASE}/doctors/search?q=${encodeURIComponent(q)}&limit=6`
    );
    if (!resp.ok) throw new Error(`Server error ${resp.status}`);
    const data = await resp.json();
    renderSearchResults(data);
  } catch (err) {
    showToast("Search failed. Please try again.");
    console.error("Search error:", err);
  } finally {
    showSkeleton(false);
  }
}

// ── Render Search Results ───────────────────────────────────────────────────
function renderSearchResults(data, isSearch = true) {
  const container = document.getElementById("docResults");
  if (!container) return;

  container.innerHTML = "";

  if (isSearch && data.specializations?.length) {
    const urgencyClass = {
      EMERGENCY: "urgency-emergency",
      HIGH: "urgency-high",
      MEDIUM: "urgency-medium",
      LOW: "urgency-low",
    };

    container.innerHTML += `
      <div class="triage-result-card" style="border:1px solid var(--border-subtle);">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.75rem;">
          <span class="label-micro" style="color:var(--accent-cyan);">📋 Medical Triage Analysis</span>
          <span class="badge ${urgencyClass[data.urgency] || ''}" style="border:1px solid;">${data.urgency}</span>
        </div>
        <div style="font-size:0.85rem;color:var(--text-secondary);display:flex;flex-direction:column;gap:0.5rem;">
          <p><strong style="color:white;">Specialist Needed:</strong> ${esc(data.specializations.join(", "))}</p>
          <p><strong style="color:white;">Home Advice:</strong> ${esc(data.home_advice)}</p>
        </div>
      </div>
    `;
  }

  if (!data.doctors?.length) {
    container.innerHTML += `
      <div class="tech-card text-center" style="padding:3rem 2rem;">
        <span style="font-size:3rem;opacity:0.6;">🔍</span>
        <h3 style="color:white;font-weight:800;font-size:1.15rem;margin-top:1rem;">No specialists found</h3>
        <p style="font-size:0.85rem;margin-top:0.5rem;">Try adjusting your symptoms or search filters.</p>
      </div>`;
    return;
  }

  data.doctors.forEach((doc) => {
    window.doctorCache = window.doctorCache || {};
    const docId = doc._id || doc.id || "";
    window.doctorCache[docId] = doc.availability || {};

    const card = `
      <div class="tech-card" style="padding:1.25rem;display:flex;align-items:center;gap:1.25rem;flex-wrap:wrap;">
        <div style="display:flex;align-items:center;gap:1rem;flex:1;min-width:240px;">
          <div style="width:56px;height:56px;border-radius:16px;background:rgba(0,242,254,0.06);border:1px solid rgba(0,242,254,0.15);display:flex;align-items:center;justify-content:center;font-size:1.6rem;flex-shrink:0;">👨‍⚕️</div>
          <div style="min-width:0;">
            <h3 style="font-weight:800;color:white;font-size:1rem;font-family:var(--font-display);">${esc(doc.name)}</h3>
            <p style="font-size:0.8rem;font-weight:700;color:var(--accent-cyan);margin-top:2px;">${esc(doc.specialization)} • ${esc(doc.location)}</p>
            <div style="display:flex;gap:0.75rem;margin-top:0.5rem;font-size:0.7rem;color:var(--text-muted);font-weight:600;">
              <span style="color:var(--accent-teal);">★ ${doc.rating || "4.5"} (${doc.total_reviews || 0})</span>
              <span>💰 PKR ${doc.consultation_fee || 1500}</span>
              <span>🕒 ${doc.experience_years || 5} yrs</span>
            </div>
          </div>
        </div>
        <a href="/doctor-profile.html?id=${docId}&symptoms=${encodeURIComponent(document.getElementById('searchInput')?.value.trim() || '')}" class="btn btn-primary" style="white-space:nowrap;">Book Slot</a>
      </div>
    `;
    container.insertAdjacentHTML("beforeend", card);
  });
}

// ── Load Featured Doctors by Default ────────────────────────────────────────
async function loadFeaturedDoctors() {
  showSkeleton(true);
  try {
    const resp = await fetch(`${API_BASE}/doctors/?limit=9`);
    if (!resp.ok) throw new Error(`Server error ${resp.status}`);
    const doctors = await resp.json();
    renderSearchResults({ doctors }, false);
  } catch (err) {
    showToast("Failed to load doctors. Please try again.");
    console.error("Load featured error:", err);
  } finally {
    showSkeleton(false);
  }
}

// ── Analysis Banner ─────────────────────────────────────────────────────────
function showAnalysisBanner(data) {
  const urgencyColors = {
    EMERGENCY: "bg-red-950/40 text-red-400 border border-red-500/20",
    HIGH: "bg-orange-950/40 text-orange-400 border border-orange-500/20",
    MEDIUM: "bg-yellow-950/40 text-yellow-400 border border-yellow-500/20",
    LOW: "bg-green-950/40 text-green-400 border border-green-500/20",
  };

  const banner = document.getElementById("analysisBanner");
  if (!banner) return;

  const advice = document.getElementById("bannerAdvice");
  const spec = document.getElementById("bannerSpec");
  const urgencyEl = document.getElementById("bannerUrgency");

  if (advice) advice.textContent = data.home_advice || "—";
  if (spec) spec.textContent = data.specializations?.join(", ") || "—";
  if (urgencyEl) {
    urgencyEl.textContent = data.urgency || "—";
    urgencyEl.className = `px-3 py-1 rounded-full text-xs font-bold ${urgencyColors[data.urgency] || "bg-slate-100 text-slate-600"
      }`;
  }

  banner.classList.remove("hidden");
}

function hideAnalysisBanner() {
  const banner = document.getElementById("analysisBanner");
  if (banner) banner.classList.add("hidden");
}

// ── Skeleton Toggle ─────────────────────────────────────────────────────────
function showSkeleton(visible) {
  const container = document.getElementById("docResults");
  if (!container) return;
  if (visible) {
    container.innerHTML = `
      <div class="skeleton h-24 w-full mb-4"></div>
      <div class="skeleton h-24 w-full mb-4"></div>
      <div class="skeleton h-24 w-full mb-4"></div>
    `;
  }
}

// ── Auto-init: bind Enter key and query params ──────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const searchInput = document.getElementById("searchInput");
  if (searchInput) {
    searchInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") handleSearch();
    });

    // Auto-search if ?q= param present
    const q = new URLSearchParams(window.location.search).get("q");
    if (q) {
      searchInput.value = q;
      handleSearch();
    } else {
      loadFeaturedDoctors();
    }
  }
});
