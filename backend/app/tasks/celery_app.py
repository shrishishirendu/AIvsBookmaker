"""Celery app + Beat schedule (BUILD_SPEC §7 auto-triggers, Phase 2).

We don't schedule one timer per match. Instead Beat runs `scan` every few
minutes; scan looks at every match and, based on now vs kickoff, enqueues:

  * T-4h  → predict_and_publish  (run the round, commit hashes, post pre-match cards)
  * kickoff → lock              (freeze the predictions; DB-enforced)
  * full-whistle → settle       (poll result, reveal, score, post-match cards)

This is resilient to missed ticks and restarts — each scan reconciles state.
The broker/result backend is Redis (settings.redis_url).
"""
from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from ..config import settings

celery_app = Celery(
    "disagreement_engine",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    beat_schedule={
        "scan-every-5-min": {
            "task": "app.tasks.jobs.scan",
            "schedule": crontab(minute="*/5"),
        },
        "personalities-nightly": {
            "task": "app.tasks.jobs.recompute_personalities",
            "schedule": crontab(hour=3, minute=0),
        },
    },
)

# ensure tasks are registered when the worker imports the app
from . import jobs  # noqa: E402,F401
