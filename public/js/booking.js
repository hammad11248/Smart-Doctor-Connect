/**
 * Smart Doctor Connect AI — Booking Flow (booking.js)
 * Handles appointment booking modal, time slot management, and form submission.
 */

// ── Booking State ───────────────────────────────────────────────────────────
let activeDoctorId = null;
let activeDoctorSlots = {};

// ── Open Booking Modal ──────────────────────────────────────────────────────
function openBooking(doctorId, doctorName, availability) {
  activeDoctorId = doctorId;
  activeDoctorSlots = availability || {};

  const modal = document.getElementById("bookingModal");
  const nameEl = document.getElementById("modalDoctorName");
  if (!modal) return;

  if (nameEl) nameEl.textContent = `with ${doctorName}`;

  // Set date min to today
  const today = getTodayStr();
  const dateInput = document.getElementById("bookDate");
  if (dateInput) {
    dateInput.min = today;
    dateInput.value = today;
    updateTimeSlots(today);
    dateInput.onchange = () => updateTimeSlots(dateInput.value);
  }

  modal.classList.remove("hidden");

  const firstInput = document.getElementById("bookPatientName");
  if (firstInput) firstInput.focus();
}

// ── Update Time Slots Based on Date ─────────────────────────────────────────
async function updateTimeSlots(dateStr) {
  const day = getDayName(dateStr);
  const slots = activeDoctorSlots[day] || [];
  const sel = document.getElementById("bookTimeSlot");
  if (!sel) return;

  sel.innerHTML = `<option value="">Checking availability...</option>`;

  try {
    const resp = await fetch(`${API_BASE}/appointments/available-slots/${activeDoctorId}?date=${dateStr}`);
    if (resp.ok) {
      const data = await resp.json();
      const booked = new Set(data.booked_slots || []);
      
      sel.innerHTML = slots.length
        ? slots.map((s) => {
            const isBooked = booked.has(s);
            if (isBooked) {
              return `<option value="${s}" disabled class="text-slate-600 bg-slate-900">${s} (Booked)</option>`;
            }
            return `<option value="${s}" class="text-white">${s}</option>`;
          }).join("")
        : `<option value="">No slots available for ${day}</option>`;
    } else {
      throw new Error("Failed to fetch slots");
    }
  } catch (err) {
    console.error("Availability check failed:", err);
    // Fallback if API fails
    sel.innerHTML = slots.length
      ? slots.map((s) => `<option value="${s}" class="text-white">${s}</option>`).join("")
      : `<option value="">No slots available for ${day}</option>`;
  }
}

// ── Close Modal ─────────────────────────────────────────────────────────────
function closeModal() {
  const modal = document.getElementById("bookingModal");
  if (modal) modal.classList.add("hidden");
  activeDoctorId = null;
}

// ── Submit Booking ──────────────────────────────────────────────────────────
async function submitBooking() {
  const name = document.getElementById("bookPatientName")?.value.trim();
  const contact = document.getElementById("bookPatientContact")?.value.trim();
  const email = document.getElementById("bookPatientEmail")?.value.trim();
  const date = document.getElementById("bookDate")?.value;
  const slot = document.getElementById("bookTimeSlot")?.value;
  const ctype = document.getElementById("bookConsultType")?.value;
  const symptoms = document.getElementById("bookSymptoms")?.value.trim();
  const docName = document
    .getElementById("modalDoctorName")
    ?.textContent.replace("with ", "");

  if (!name || !contact || !email || !date || !slot) {
    showToast("Please fill in all required fields.");
    return;
  }

  try {
    const resp = await fetch(`${API_BASE}/appointments/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        doctor_id: activeDoctorId,
        doctor_name: docName,
        patient_name: name,
        patient_contact: contact,
        patient_email: email,
        date,
        time_slot: slot,
        consultation_type: ctype,
        symptoms: symptoms || null,
      }),
    });

    if (resp.status === 409) {
      showToast("⚠️ That slot is already booked. Please choose another.");
      return;
    }

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      let msg = "Booking failed";
      if (Array.isArray(err.detail)) {
        msg = err.detail.map((d) => {
          if (d.loc && d.loc.includes("patient_contact")) {
            return "Please enter a valid Pakistani contact number (e.g., +92 300 1234567 or 03001234567).";
          }
          if (d.loc && d.loc.includes("patient_email")) {
            return "Please enter a valid email address.";
          }
          return d.msg || "Invalid field";
        }).join(" ");
      } else if (typeof err.detail === "string") {
        msg = err.detail;
      }
      throw new Error(msg);
    }

    const data = await resp.json();
    closeModal();

    // Show confirmation with queue info
    const waitMsg = data.predicted_wait_minutes
      ? ` Estimated wait: ~${data.predicted_wait_minutes} min.`
      : "";
    showToast(
      `✅ Appointment booked! Queue #${data.queue_position}.${waitMsg}`,
      5000
    );
  } catch (err) {
    showToast(err.message || "Booking failed. Please try again.");
    console.error("Booking error:", err);
  }
}

// ── Init: backdrop close + keyboard shortcuts ───────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const modal = document.getElementById("bookingModal");
  if (modal) {
    modal.addEventListener("click", (e) => {
      if (e.target === modal) closeModal();
    });
  }

  // Escape key closes modal
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeModal();
  });
});
