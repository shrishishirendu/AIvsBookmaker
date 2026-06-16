"""In-process scheduler — Docker-free alternative to Celery worker + beat.

When `RUN_SCHEDULER=true`, the FastAPI app starts a background asyncio loop that
reconciles every match against the clock and runs the same task cores Celery
would (`app.tasks.jobs`): predict+publish at T-4h, lock at kickoff, settle at the
full whistle. No Redis, no broker, no second process.

This makes a single `uvicorn` process fully self-running. The Celery path
remains available for the Postgres+Redis Docker deployment.
"""
from __future__ import annotations

import asyncio
import logging

from .config import settings
from .db import SessionLocal
from .tasks import jobs

logger = logging.getLogger(__name__)

_ACTIONS = {
    "predict_and_publish": jobs.predict_and_publish_async,
    "lock": jobs.lock_async,
    "settle": jobs.settle_async,
}


async def _tick() -> None:
    async with SessionLocal() as session:
        actions = await jobs.scan_async(session)
    if actions:
        logger.info("scheduler: %d action(s) due: %s",
                    len(actions), [(a["action"], a["match_id"]) for a in actions])
    for a in actions:
        fn = _ACTIONS.get(a["action"])
        if fn is None:
            continue
        try:
            async with SessionLocal() as session:
                result = await fn(session, a["match_id"])
                await session.commit()
            logger.info("scheduler: ran %s for match %s -> %s",
                        a["action"], a["match_id"], _summary(result))
        except Exception as exc:  # never let one match kill the loop
            logger.warning("scheduler: %s for match %s failed: %s",
                           a["action"], a["match_id"], exc)


def _summary(result: dict) -> str:
    if "published" in result and isinstance(result["published"], dict):
        p = result["published"]
        return f"{result.get('status', result.get('action'))}, published {p.get('posted')}/{p.get('total')}"
    return str(result.get("status", result.get("action", "ok")))


async def run_scheduler_loop(stop: asyncio.Event) -> None:
    interval = settings.scheduler_interval_seconds
    logger.info("in-process scheduler started (every %ss, dry_run=%s)",
                interval, settings.publish_dry_run)
    while not stop.is_set():
        try:
            await _tick()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("scheduler tick failed: %s", exc)
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass
    logger.info("in-process scheduler stopped")
