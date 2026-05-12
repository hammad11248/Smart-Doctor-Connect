"""
Smart Doctor Connect AI — MongoDB Connection Manager
Uses Motor (async) driver. Indexes are created on startup.
"""

import os
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


async def connect_db() -> None:
    global _client, _db

    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    _client = AsyncIOMotorClient(uri)
    _db = _client.get_default_database(default="smart_doctor_db")

    # ── Indexes ────────────────────────────────────────────────────────────────
    # Doctors: text search + unique email
    await _db.doctors.create_index([("name", "text"), ("specialization", "text"), ("bio", "text")])
    await _db.doctors.create_index("email", unique=True)
    await _db.doctors.create_index("specialization")
    await _db.doctors.create_index("location")
    await _db.doctors.create_index("is_available")

    # Appointments: prevent double-booking + fast lookup
    await _db.appointments.create_index(
        [("doctor_id", 1), ("date", 1), ("time_slot", 1)], unique=True
    )
    await _db.appointments.create_index("doctor_id")
    await _db.appointments.create_index("patient_email")

    # Messages
    await _db.messages.create_index("doctor_id")
    await _db.messages.create_index("created_at")


async def close_db() -> None:
    global _client
    if _client:
        _client.close()


def get_db() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("Database not connected. Call connect_db() first.")
    return _db
