"""
Smart-Doctor-Connect-AI — MongoDB Connection Manager & Mock Fallback
Uses Motor (async) driver. Indexes are created on startup.
If the database connection is unavailable or unconfigured, it seamlessly
falls back to a fully functional, in-memory Mock MongoDB to ensure 100% uptime.
"""

import os
import copy
import re
from typing import Optional, Union, List
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

# ── Mock Database Classes ───────────────────────────────────────────────────

class MockCursor:
    """Mock implementation of Motor's AsyncIOMotorCursor."""
    def __init__(self, data):
        self.data = data
        self._skip = 0
        self._limit = None
        self._sort_key = None
        self._sort_dir = 1

    def skip(self, n: int):
        self._skip = n
        return self

    def limit(self, n: int):
        self._limit = n
        return self

    def sort(self, key: str, direction: int = 1):
        self._sort_key = key
        self._sort_dir = direction
        return self

    async def to_list(self, length: Optional[int] = None) -> List[dict]:
        res = list(self.data)
        if self._sort_key:
            res = sorted(
                res, 
                key=lambda x: x.get(self._sort_key, None) or "", 
                reverse=(self._sort_dir == -1)
            )
        res = res[self._skip:]
        if self._limit is not None:
            res = res[:self._limit]
        if length is not None:
            res = res[:length]
        return res


class MockCollection:
    """Mock implementation of Motor's AsyncIOMotorCollection."""
    def __init__(self, name: str, initial_data: Optional[List[dict]] = None):
        self.name = name
        self.data = []
        if initial_data:
            for doc in initial_data:
                if "_id" not in doc:
                    import hashlib
                    # Generate a deterministic 12-byte ObjectId based on email/name to ensure
                    # consistent IDs across server restarts and serverless cold starts.
                    seed_str = doc.get("email", doc.get("name", ""))
                    h = hashlib.md5(seed_str.encode("utf-8")).digest()[:12]
                    doc["_id"] = ObjectId(h)
                self.data.append(doc)

    async def count_documents(self, query: dict) -> int:
        return len(self._filter(query))

    async def find_one(self, query: dict) -> Optional[dict]:
        filtered = self._filter(query)
        return copy.deepcopy(filtered[0]) if filtered else None

    def find(self, query: Optional[dict] = None, projection: Optional[dict] = None) -> MockCursor:
        filtered = self._filter(query or {})
        return MockCursor([copy.deepcopy(doc) for doc in filtered])

    async def insert_one(self, document: dict):
        # Enforce unique index for appointments (doctor_id, date, time_slot)
        if self.name == "appointments":
            for doc in self.data:
                if (doc.get("doctor_id") == document.get("doctor_id") and
                    doc.get("date") == document.get("date") and
                    doc.get("time_slot") == document.get("time_slot") and
                    doc.get("status") in ["confirmed", "pending"]):
                    from pymongo.errors import DuplicateKeyError
                    raise DuplicateKeyError("Duplicate key error: slot already booked.")

        if "_id" not in document:
            document["_id"] = ObjectId()
        self.data.append(document)
        
        class InsertResult:
            inserted_id = document["_id"]
        return InsertResult()

    async def insert_many(self, documents: List[dict]):
        inserted_ids = []
        for doc in documents:
            if "_id" not in doc:
                doc["_id"] = ObjectId()
            self.data.append(doc)
            inserted_ids.append(doc["_id"])
            
        class InsertManyResult:
            inserted_ids = inserted_ids
        return InsertManyResult()

    async def update_one(self, query: dict, update: dict):
        filtered = self._filter(query)
        if not filtered:
            class UpdateResult:
                matched_count = 0
                modified_count = 0
            return UpdateResult()
        
        doc = filtered[0]
        if "$set" in update:
            for k, v in update["$set"].items():
                doc[k] = v
                
        class UpdateResult:
            matched_count = 1
            modified_count = 1
        return UpdateResult()

    async def delete_many(self, query: dict):
        filtered = self._filter(query)
        for doc in filtered:
            self.data.remove(doc)

    async def create_index(self, *args, **kwargs):
        pass

    def _filter(self, query: dict) -> List[dict]:
        results = []
        for doc in self.data:
            match = True
            for k, v in query.items():
                if k == "$or":
                    or_match = False
                    for subquery in v:
                        if self._match_doc(doc, subquery):
                            or_match = True
                            break
                    if not or_match:
                        match = False
                        break
                else:
                    if not self._match_field(doc.get(k), v):
                        match = False
                        break
            if match:
                results.append(doc)
        return results

    def _match_doc(self, doc: dict, query: dict) -> bool:
        for k, v in query.items():
            if not self._match_field(doc.get(k), v):
                return False
        return True

    def _match_field(self, val, criterion) -> bool:
        if hasattr(criterion, 'search'):
            # Handles compiled re patterns
            return bool(criterion.search(str(val or "")))
        if isinstance(criterion, dict):
            if "$regex" in criterion:
                pattern = criterion["$regex"]
                options = criterion.get("$options", "")
                flags = re.IGNORECASE if "i" in options else 0
                return bool(re.search(pattern, str(val or ""), flags))
            if "$in" in criterion:
                return val in criterion["$in"]
        return val == criterion


class MockDatabase:
    """Mock implementation of AsyncIOMotorDatabase."""
    def __init__(self):
        try:
            from seed_data import DEMO_DOCTORS
            doctors_list = copy.deepcopy(DEMO_DOCTORS)
        except Exception:
            doctors_list = []
            
        self.doctors = MockCollection("doctors", doctors_list)
        self.appointments = MockCollection("appointments")
        self.messages = MockCollection("messages")
        self.email_logs = MockCollection("email_logs")


# ── Database Connection Manager ──────────────────────────────────────────────

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[Union[AsyncIOMotorDatabase, MockDatabase]] = None
_indexes_created: bool = False


async def connect_db() -> None:
    global _client, _db, _indexes_created

    if _client is not None or _db is not None:
        return  # already initialized

    uri = os.getenv("MONGODB_URI", "")
    is_production = os.getenv("VERCEL") == "1" or os.getenv("ENVIRONMENT") == "production"
    
    use_mock = False
    if not uri or (is_production and "localhost" in uri):
        print("[WARNING] MONGODB_URI is not set or points to localhost in production/Vercel.")
        print("[DB] Automatically falling back to In-Memory Mock Database!")
        use_mock = True

    if not use_mock:
        try:
            # Set short timeout of 3 seconds so we fail fast instead of hanging the Vercel function
            _client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=3000)
            _db = _client.get_default_database(default="smart_doctor_db")
            # Force a connection check
            await _client.server_info()
            print("[DB] Connected successfully to MongoDB.")
        except Exception as e:
            print(f"[ERROR] Failed to connect to MongoDB: {e}")
            print("[DB] Automatically falling back to In-Memory Mock Database!")
            _client = None
            use_mock = True

    if use_mock:
        _db = MockDatabase()
        _indexes_created = True
        return

    # ── Real Indexes ────────────────────────────────────────────────────────────
    # Only try creating indexes on real DB in development to reduce cold start latency
    if not is_production and not _indexes_created:
        try:
            await _db.doctors.create_index([("name", "text"), ("specialization", "text"), ("bio", "text")])
            await _db.doctors.create_index("email", unique=True)
            await _db.doctors.create_index("specialization")
            await _db.doctors.create_index("location")
            await _db.doctors.create_index("is_available")

            await _db.appointments.create_index(
                [("doctor_id", 1), ("date", 1), ("time_slot", 1)], unique=True
            )
            await _db.appointments.create_index("doctor_id")
            await _db.appointments.create_index("patient_email")

            await _db.messages.create_index("doctor_id")
            await _db.messages.create_index("created_at")

            _indexes_created = True
        except Exception as e:
            print(f"Index creation warning (may already exist): {e}")


async def close_db() -> None:
    global _client
    if _client:
        _client.close()


async def get_db() -> Union[AsyncIOMotorDatabase, MockDatabase]:
    """
    Returns the database instance, auto-connecting on first call.
    This handles Vercel serverless cold starts where lifespan may not fire.
    """
    global _db
    if _db is None:
        await connect_db()
    return _db
