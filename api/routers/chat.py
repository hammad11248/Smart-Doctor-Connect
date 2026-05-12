"""
Smart Doctor Connect AI — Chat Router
Endpoints: send message (AI receptionist), get chat history.
When a doctor is offline, the AI generates a response, stores the message,
sends an email notification, and schedules a follow-up reminder.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List

from bson import ObjectId
from fastapi import APIRouter, HTTPException, status

from api.database import get_db
from api.models import MessageCreate, MessageInDB
from api.services.ai_agent import ai_agent
from api.services.email_service import (
    send_doctor_notification,
    send_followup_reminder,
)

router = APIRouter()


def _msg_to_response(doc: dict) -> MessageInDB:
    """Convert a MongoDB message document to a MessageInDB response."""
    doc["_id"] = str(doc["_id"])
    return MessageInDB(**doc)


# ── Send Message (AI Receptionist) ────────────────────────────────────────────
@router.post(
    "/message",
    response_model=MessageInDB,
    status_code=status.HTTP_201_CREATED,
    summary="Send a message to a doctor (AI responds if offline)",
)
async def send_message(payload: MessageCreate):
    db = get_db()

    # Verify doctor exists
    try:
        doctor_oid = ObjectId(payload.doctor_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid doctor ID format.")

    doctor = await db.doctors.find_one({"_id": doctor_oid})
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found.")

    doctor_name = doctor.get("name", "the doctor")
    doctor_email = doctor.get("email", "")
    doctor_available = doctor.get("is_available", False)

    # Generate AI response
    ai_response = await ai_agent.generate_response(
        patient_name=payload.patient_name,
        message=payload.message,
        doctor_name=doctor_name,
        doctor_available=doctor_available,
    )

    # Store message in database
    msg_dict = payload.model_dump()
    msg_dict["ai_response"] = ai_response
    msg_dict["doctor_available"] = doctor_available
    msg_dict["created_at"] = datetime.utcnow()

    result = await db.messages.insert_one(msg_dict)
    created = await db.messages.find_one({"_id": result.inserted_id})

    # If doctor is offline, send email notification and schedule follow-up
    if not doctor_available and doctor_email:
        await send_doctor_notification(
            doctor_email=doctor_email,
            doctor_name=doctor_name,
            patient_name=payload.patient_name,
            patient_contact=payload.patient_contact,
            message=payload.message,
        )

        # Schedule a follow-up reminder (using APScheduler if available)
        try:
            await _schedule_followup(
                patient_contact=payload.patient_contact,
                patient_name=payload.patient_name,
                doctor_name=doctor_name,
                original_message=payload.message,
            )
        except Exception:
            pass  # Non-critical — don't fail the request

    return _msg_to_response(created)


# ── Get Chat History ──────────────────────────────────────────────────────────
@router.get(
    "/history/{doctor_id}",
    response_model=List[MessageInDB],
    summary="Get chat history for a doctor",
)
async def get_chat_history(doctor_id: str, limit: int = 50):
    db = get_db()

    # Verify doctor exists
    try:
        ObjectId(doctor_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid doctor ID format.")

    cursor = (
        db.messages.find({"doctor_id": doctor_id})
        .sort("created_at", -1)
        .limit(limit)
    )
    docs = await cursor.to_list(length=limit)

    # Return in chronological order (oldest first)
    docs.reverse()
    return [_msg_to_response(d) for d in docs]


# ── Follow-up Scheduler ──────────────────────────────────────────────────────
async def _schedule_followup(
    patient_contact: str | None,
    patient_name: str,
    doctor_name: str,
    original_message: str,
) -> None:
    """
    Schedule a follow-up reminder 4 hours after the initial message.
    Uses APScheduler for async job scheduling.
    If APScheduler is unavailable, logs and skips gracefully.
    """
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.date import DateTrigger

        scheduler = AsyncIOScheduler()
        run_time = datetime.utcnow() + timedelta(hours=4)

        scheduler.add_job(
            send_followup_reminder,
            trigger=DateTrigger(run_date=run_time),
            kwargs={
                "patient_email": patient_contact or "",
                "patient_name": patient_name,
                "doctor_name": doctor_name,
                "original_message": original_message,
            },
            id=f"followup_{patient_name}_{datetime.utcnow().timestamp()}",
            replace_existing=True,
        )

        if not scheduler.running:
            scheduler.start()

        print(
            f"⏰ Follow-up reminder scheduled for {patient_name} "
            f"regarding {doctor_name} at {run_time.isoformat()}"
        )
    except Exception as e:
        print(f"⚠️ Could not schedule follow-up (non-critical): {e}")
