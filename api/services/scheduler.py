"""
Scheduler — only used in local development.
On Vercel serverless, APScheduler is not installed and this is skipped.
"""

import os


class _NoOpScheduler:
    """Stub that silently does nothing when APScheduler is unavailable."""
    running = False
    def start(self): pass
    def shutdown(self): pass
    def add_job(self, *a, **kw): pass


# Only import APScheduler in development (it's not in production requirements)
if os.getenv("ENVIRONMENT", "development") == "development":
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        scheduler = AsyncIOScheduler()
    except ImportError:
        scheduler = _NoOpScheduler()
else:
    scheduler = _NoOpScheduler()
