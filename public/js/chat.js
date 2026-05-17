/**
 * Smart Doctor Connect AI — Real-time Chat Interface (chat.js)
 * Handles the AI receptionist chatbot on doctor profile pages.
 * Sends messages to the backend, displays AI responses, and loads chat history.
 */

// ── Chat State ──────────────────────────────────────────────────────────────
let chatDoctorId = null;
let chatSending = false;

// ── Initialize Chat ─────────────────────────────────────────────────────────
function initChat(doctorId) {
  chatDoctorId = doctorId;
  if (doctorId) {
    loadChatHistory(doctorId);
  }
}

// ── Send Message ────────────────────────────────────────────────────────────
async function sendChatMessage() {
  if (chatSending) return;

  const nameInput = document.getElementById("chatName");
  const contactInput = document.getElementById("chatContact");
  const msgInput = document.getElementById("chatMessage");

  if (!nameInput || !msgInput) return;

  const name = nameInput.value.trim();
  const contact = contactInput?.value.trim() || null;
  const message = msgInput.value.trim();

  if (!name) {
    showToast("Please enter your name.");
    nameInput.focus();
    return;
  }
  if (!message) {
    showToast("Please type a message.");
    msgInput.focus();
    return;
  }
  if (!chatDoctorId) {
    showToast("No doctor selected.");
    return;
  }

  // Add patient bubble immediately
  addChatBubble(message, "patient", name);
  msgInput.value = "";
  chatSending = true;

  // Show typing indicator
  const typingId = addTypingIndicator();

  try {
    const resp = await fetch(`${API_BASE}/chat/message`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        doctor_id: chatDoctorId,
        patient_name: name,
        patient_contact: contact,
        message: message,
      }),
    });

    removeTypingIndicator(typingId);

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to send message");
    }

    const data = await resp.json();
    addChatBubble(data.ai_response, "ai", "AI Receptionist");

    // Show notification about doctor availability
    if (!data.doctor_available) {
      showToast("📧 Doctor has been notified via email.", 4000);
    }
  } catch (err) {
    removeTypingIndicator(typingId);
    addChatBubble(
      "Sorry, something went wrong. Please try again.",
      "ai",
      "System"
    );
    console.error("Chat error:", err);
  } finally {
    chatSending = false;
  }
}

// ── Load Chat History ───────────────────────────────────────────────────────
async function loadChatHistory(doctorId) {
  const container = document.getElementById("chatMessages");
  if (!container) return;

  try {
    const resp = await fetch(
      `${API_BASE}/chat/history/${doctorId}?limit=20`
    );
    if (!resp.ok) return;

    const messages = await resp.json();
    if (!messages.length) {
      addChatBubble(
        "Welcome! Send a message and our AI receptionist will assist you.",
        "ai",
        "AI Receptionist"
      );
      return;
    }

    messages.forEach((msg) => {
      addChatBubble(msg.message, "patient", msg.patient_name);
      addChatBubble(msg.ai_response, "ai", "AI Receptionist");
    });
  } catch (err) {
    console.error("Failed to load chat history:", err);
  }
}

// ── Add Chat Bubble ─────────────────────────────────────────────────────────
function addChatBubble(text, type, sender) {
  const container = document.getElementById("chatMessages");
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
    <p>${esc(text)}</p>
  `;

  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
}

// ── Typing Indicator ────────────────────────────────────────────────────────
function addTypingIndicator() {
  const container = document.getElementById("chatMessages");
  if (!container) return null;

  const id = "typing-" + Date.now();
  const indicator = document.createElement("div");
  indicator.id = id;
  indicator.className = "chat-bubble-ai";
  indicator.style.cssText = "margin-right:auto;padding:1rem 1.25rem;max-width:80%;font-size:0.85rem;display:flex;align-items:center;gap:0.75rem;";
  indicator.innerHTML = `
    <span class="label-micro" style="color:var(--accent-cyan);">System AI</span>
    <div class="typing-indicator">
      <span class="typing-dot"></span>
      <span class="typing-dot"></span>
      <span class="typing-dot"></span>
    </div>`;

  container.appendChild(indicator);
  container.scrollTop = container.scrollHeight;
  return id;
}

function removeTypingIndicator(id) {
  if (!id) return;
  const el = document.getElementById(id);
  if (el) el.remove();
}

// ── Init: keyboard shortcut ─────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const chatInput = document.getElementById("chatMessage");
  if (chatInput) {
    chatInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendChatMessage();
      }
    });
  }
});

// ── Finish Chat and Summarize ───────────────────────────────────────────────
async function finishChatAndSummarize() {
  if (!chatDoctorId) {
    showToast("No doctor selected.");
    return;
  }

  const nameInput = document.getElementById("chatName");
  const name = nameInput?.value.trim() || "Patient";

  const container = document.getElementById("chatMessages");
  if (!container || !container.children.length) {
    showToast("No conversation to summarize.");
    return;
  }

  const history = [];
  Array.from(container.children).forEach((bubble) => {
    if (bubble.id && bubble.id.startsWith("typing")) return;
    const isPatient = bubble.className.includes("self-end");
    const role = isPatient ? "Patient" : "AI";
    const pTag = bubble.querySelector("p");
    if (pTag) {
      history.push({ role, content: pTag.textContent });
    }
  });

  if (!history.length) return;

  const btn = event.currentTarget;
  const originalText = btn.innerHTML;
  btn.innerHTML = `<span class="animate-pulse">Syncing Briefing...</span>`;
  btn.disabled = true;

  try {
    const resp = await fetch(`${API_BASE}/chat/summary`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        doctor_id: chatDoctorId,
        patient_name: name,
        chat_history: history,
      }),
    });

    if (!resp.ok) throw new Error("Failed to generate summary");
    
    const data = await resp.json();
    showToast("✅ Triage summary successfully linked to appointment!");

    // Agentic workflow: autofill the Quick Booking Form
    const qbName = document.getElementById("qbName");
    const qbContact = document.getElementById("qbContact");
    const qbSymptoms = document.getElementById("qbSymptoms");
    const chatContact = document.getElementById("chatContact");

    if (qbName && name) qbName.value = name;
    if (qbContact && chatContact?.value) qbContact.value = chatContact.value;
    if (qbSymptoms && data.triage_summary) {
      qbSymptoms.value = data.triage_summary;
      // Visually flash the symptoms field to show sync
      qbSymptoms.classList.add("border-accentTeal", "shadow-neonTeal");
      setTimeout(() => {
        qbSymptoms.classList.remove("border-accentTeal", "shadow-neonTeal");
      }, 1500);
    }

    // Agentic Doctor Matching
    const matchResp = await fetch(`${API_BASE}/agents/match-doctor`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        triage_summary: data.triage_summary,
      }),
    });

    if (matchResp.ok) {
      const matchData = await matchResp.json();
      displayAgentRecommendations(matchData);
    }

  } catch (err) {
    console.error(err);
    showToast("⚠️ Could not generate summary. Please check connection.");
  } finally {
    btn.innerHTML = originalText;
    btn.disabled = false;
  }
}

function displayAgentRecommendations(matchData) {
  const container = document.getElementById("chatMessages");
  if (!container) return;

  const bubble = document.createElement("div");
  bubble.className = "chat-bubble-ai";
  bubble.style.cssText = "margin-right:auto;padding:1rem 1.25rem;max-width:85%;";
  
  let docsHtml = matchData.doctors.map(d => {
    return `<div class="tech-card" style="padding:1rem;margin-top:0.75rem;">
      <p style="font-weight:800;color:white;font-size:0.85rem;">${d.name}</p>
      <p style="font-size:0.75rem;font-weight:700;color:var(--accent-cyan);margin-top:0.25rem;">${d.specialization} • ${d.location}</p>
    </div>`;
  }).join("");

  bubble.innerHTML = `
    <div style="display:flex;align-items:center;gap:0.4rem;margin-bottom:0.4rem;opacity:0.8;">
      <span class="label-micro" style="color:var(--accent-cyan);">Agent Specialist Matching</span>
    </div>
    <p style="font-size:0.85rem;line-height:1.6;margin-bottom:0.75rem;color:var(--text-secondary);">${matchData.reasoning}</p>
    ${docsHtml}
  `;
  
  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
}

