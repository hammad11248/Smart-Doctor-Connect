"""
Smart Doctor Connect AI — FastAPI Entry Point
Handles app lifecycle, CORS, rate limiting, and router registration.
"""

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from api.database import connect_db, close_db
from api.routers import doctors, appointments, chat

# ── Environment ──────────────────────────────────────────────────────────────
load_dotenv()

ENVIRONMENT = os.getenv("ENVIRONMENT", "production")

# ── Rate Limiter ─────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


# ── Lifespan (replaces deprecated on_event) ──────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Connect to MongoDB on startup; close connection on shutdown."""
    await connect_db()
    yield
    await close_db()


# ── App Factory ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Smart Doctor Connect AI",
    description="AI-powered doctor discovery and appointment booking for Pakistan",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if ENVIRONMENT != "production" else None,
    redoc_url="/api/redoc" if ENVIRONMENT != "production" else None,
)

# ── Middleware ────────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Tighten in production to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(doctors.router,      prefix="/api/doctors",      tags=["Doctors"])
app.include_router(appointments.router, prefix="/api/appointments",  tags=["Appointments"])
app.include_router(chat.router,         prefix="/api/chat",          tags=["Chat"])

# ── Static Files (serves /public when running locally) ────────────────────────
if ENVIRONMENT == "development":
    app.mount("/", StaticFiles(directory="public", html=True), name="static")


# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/api/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "environment": ENVIRONMENT}
