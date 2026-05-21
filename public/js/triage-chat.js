/**
 * Smart Doctor Connect — Home Page Floating Triage Assistant (triage-chat.js)
 * Manages the virtual patient intake assistant on the landing page.
 * Sends symptom inputs to the backend triage endpoint and displays doctor cards directly in-chat.
 */

// ── State ────────────────────────────────────────────────────────────────────
let triageChatOpen = false;
let triageSending = false;
let triagePatientName = "";
let latestSymptoms = "";

// ── Toggle Widget ────────────────────────────────────────────────────────────
function toggleTriageChat() {
  const windowEl = document.getElementById("triageChatWindow");
  const badge = document.getElementById("triageChatBadge");
  
  if (!windowEl) return;
  
  triageChatOpen = !triageChatOpen;
  windowEl.classList.toggle("hidden", !triageChatOpen);
  
  if (triageChatOpen) {
    if (badge) badge.classList.add("hidden");
    
    // Auto-focus name input if empty
    const nameInput = document.getElementById("triagePatientName");
    if (nameInput && !triagePatientName) {
      setTimeout(() => nameInput.focus(), 100);
    } else {
      const msgInput = document.getElementById("triageMessage");
      if (msgInput) setTimeout(() => msgInput.focus(), 100);
    }
  }
}

// ── Initialize Triage Chat ───────────────────────────────────────────────────
function initTriageChat() {
  const container = document.getElementById("triageChatMessages");
  if (!container) return;

  container.innerHTML = "";
  
  addTriageBubble(
    "Hello there! I am your virtual clinical intake coordinator. Please tell me your name and describe your symptoms to help us map the best matching specialists for your needs.",
    "ai",
    "Patient Intake Assistant"
  );
}

// ── Send Message ─────────────────────────────────────────────────────────────
async function sendTriageMessage() {
  if (triageSending) return;

  const nameInput = document.getElementById("triagePatientName");
  const msgInput = document.getElementById("triageMessage");
  const formArea = document.getElementById("triageNameFormArea");

  if (!nameInput || !msgInput) return;

  const name = nameInput.value.trim();
  const message = msgInput.value.trim();

  if (!triagePatientName) {
    if (!name) {
      showToast("Please enter your name first.");
      nameInput.focus();
      return;
    }
    triagePatientName = name;
    if (formArea) {
      formArea.classList.add("hidden");
    }
  }

  if (!message) {
    showToast("Please type your symptoms.");
    msgInput.focus();
    return;
  }

  // Display user's message
  latestSymptoms = message;
  addTriageBubble(message, "patient", triagePatientName);
  msgInput.value = "";
  triageSending = true;

  const typingId = addTriageTypingIndicator();

  try {
    const resp = await fetch(`${API_BASE}/chat/triage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        patient_name: triagePatientName,
        message: message,
      }),
    });

    removeTriageTypingIndicator(typingId);

    if (!resp.ok) {
      throw new Error(`Server status: ${resp.status}`);
    }

    const data = await resp.json();
    
    // Render AI's response text
    addTriageBubble(data.ai_response, "ai", "Patient Intake Assistant");

    // Display recommendation badge
    if (data.specializations?.length) {
      addTriageRecommendationCard(data);
    }

    // Display matching doctor suggestions directly inside chat!
    if (data.doctors && data.doctors.length > 0) {
      addTriageDoctorSuggestions(data.doctors);
    }
  } catch (err) {
    removeTriageTypingIndicator(typingId);
    addTriageBubble(
      "I encountered an issue connecting to the clinical intake service. Please search your symptoms directly using the search bar above.",
      "ai",
      "Patient Intake Assistant"
    );
    console.error("Triage chat error:", err);
  } finally {
    triageSending = false;
  }
}

// ── Add Chat Bubble ──────────────────────────────────────────────────────────
function addTriageBubble(text, type, sender) {
  const container = document.getElementById("triageChatMessages");
  if (!container) return;

  const bubble = document.createElement("div");
  const isPatient = type === "patient";

  bubble.style.cssText = `max-width:80%;padding:1rem 1.25rem;font-size:0.85rem;line-height:1.6;${isPatient ? 'margin-left:auto;' : 'margin-right:auto;'}`;
  bubble.className = isPatient ? 'chat-bubble-user' : 'chat-bubble-ai';

  const timeStr = new Date().toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
  });

  bubble.innerHTML = `
    <div style="display:flex;align-items:center;gap:0.4rem;margin-bottom:0.4rem;opacity:0.8;">
      <span style="font-weight:800;font-size:0.6rem;text-transform:uppercase;letter-spacing:0.1em;color:${isPatient ? 'white' : 'var(--accent-cyan)'}">${esc(sender)}</span>
      <span style="font-size:0.55rem;opacity:0.6;">${timeStr}</span>
    </div>
    <p style="white-space:pre-line;">${esc(text)}</p>
  `;

  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
}

// ── Add Triage Recommendation Card ───────────────────────────────────────────
function addTriageRecommendationCard(data) {
  const container = document.getElementById("triageChatMessages");
  if (!container) return;

  const urgencyColors = {
    EMERGENCY: "bg-red-500 text-white",
    HIGH: "bg-orange-500 text-white",
    MEDIUM: "bg-yellow-500 text-slate-900",
    LOW: "bg-green-500 text-white",
  };

  const urgencyClass = {
    EMERGENCY: "urgency-emergency",
    HIGH: "urgency-high",
    MEDIUM: "urgency-medium",
    LOW: "urgency-low",
  };

  const card = document.createElement("div");
  card.className = "triage-result-card";
  card.style.cssText = "margin:0.5rem 0;margin-right:auto;width:90%;border:1px solid var(--border-subtle);background:rgba(0,242,254,0.03);border-left:3px solid var(--accent-cyan);border-radius:4px 16px 16px 4px;padding:1.25rem;font-size:0.85rem;";

  card.innerHTML = `
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.5rem;">
      <span class="label-micro" style="color:var(--accent-cyan);">📋 Triage Analysis</span>
      <span class="badge ${urgencyClass[data.urgency] || ''}" style="border:1px solid;">${data.urgency}</span>
    </div>
    <div style="color:var(--text-secondary);display:flex;flex-direction:column;gap:0.4rem;">
      <p><strong style="color:white;">Specialist:</strong> ${esc(data.specializations.join(", "))}</p>
      <p><strong style="color:white;">Advice:</strong> ${esc(data.home_advice)}</p>
    </div>
  `;

  container.appendChild(card);
  container.scrollTop = container.scrollHeight;
}

// ── Display Doctor Suggestions in Chat ────────────────────────────────────────
function addTriageDoctorSuggestions(doctors) {
  const container = document.getElementById("triageChatMessages");
  if (!container) return;

  const div = document.createElement("div");
  div.style.cssText = "margin-right:auto;width:90%;margin:0.5rem 0;display:flex;flex-direction:column;gap:0.5rem;";

  const label = document.createElement("div");
  label.className = "label-micro";
  label.style.marginBottom = "0.5rem";
  label.textContent = "Recommended Specialists:";
  div.appendChild(label);

  doctors.forEach((doc) => {
    window.doctorCache = window.doctorCache || {};
    window.doctorCache[doc._id] = doc.availability || {};

    const card = document.createElement("div");
    card.className = "tech-card";
    card.style.cssText = "padding:1rem;display:flex;align-items:center;justify-content:space-between;gap:0.75rem;";

    card.innerHTML = `
      <div style="display:flex;align-items:center;gap:0.75rem;min-width:0;">
        <div style="width:40px;height:40px;border-radius:50%;background:rgba(0,242,254,0.06);border:1px solid rgba(0,242,254,0.15);display:flex;align-items:center;justify-content:center;font-size:1.2rem;flex-shrink:0;">👨‍⚕️</div>
        <div style="min-width:0;">
          <h4 style="font-weight:800;color:white;font-size:0.9rem;">${esc(doc.name)}</h4>
          <p style="font-size:0.75rem;font-weight:700;color:var(--accent-cyan);margin-top:2px;">${esc(doc.specialization)} • ${esc(doc.location)}</p>
          <span style="font-size:0.7rem;color:var(--accent-teal);">★ ${doc.rating || "4.5"}</span>
        </div>
      </div>
      <button onclick="window.location.href='/doctor-profile.html?id=${doc._id}&patient_name=${encodeURIComponent(triagePatientName)}&symptoms=${encodeURIComponent(latestSymptoms)}'" 
        class="btn btn-primary" style="flex-shrink:0;padding:0.5rem 1rem;">Book</button>
    `;
    div.appendChild(card);
  });

  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

// ── Typing Indicator ─────────────────────────────────────────────────────────
function addTriageTypingIndicator() {
  const container = document.getElementById("triageChatMessages");
  if (!container) return null;

  const id = "triage-typing-" + Date.now();
  const indicator = document.createElement("div");
  indicator.id = id;
  indicator.className = "chat-bubble-ai";
  indicator.style.cssText = "margin-right:auto;padding:1rem 1.25rem;max-width:80%;font-size:0.85rem;display:flex;align-items:center;gap:0.75rem;";
  indicator.innerHTML = `
    <span class="label-micro" style="color:var(--accent-cyan);">Patient Intake System</span>
    <div class="typing-indicator">
      <span class="typing-dot"></span>
      <span class="typing-dot"></span>
      <span class="typing-dot"></span>
    </div>`;

  container.appendChild(indicator);
  container.scrollTop = container.scrollHeight;
  return id;
}

function removeTriageTypingIndicator(id) {
  if (!id) return;
  const el = document.getElementById(id);
  if (el) el.remove();
}

// ── Bind DOM Elements ────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  initTriageChat();

  const triageInput = document.getElementById("triageMessage");
  if (triageInput) {
    triageInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendTriageMessage();
      }
    });
  }
});
