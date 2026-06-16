"""Celery tasks + their async cores.

The async `*_async` functions hold all the logic and take an AsyncSession, so
they're unit-testable with no Celery/Redis. The Celery tasks are thin wrappers
that open a session and run the core via asyncio.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..ai.cost_guard import CostGuard
from ..content.service import generate_for_match
from ..db import SessionLocal
from ..football.client import FootballClient
from ..models import Match, Prediction
from ..redis_client import make_redis
from ..services import predictions as preds_svc
from ..services import standings as standings_svc
from ..services.personalities import compute_personalities
from ..services.results import ingest_result
from ..publishing import service as publish_svc
from .celery_app import celery_app

logger = logging.getLogger(__name__)

PREDICT_LEAD = timedelta(hours=4)      # T-4h: run the round + post pre-match cards
SETTLE_DELAY = timedelta(hours=2)      # ~match length before we poll for a result


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _football() -> FootballClient:
    return FootballClient(make_redis())


def _cost_guard() -> CostGuard:
    return CostGuard(make_redis())


# --- async cores ------------------------------------------------------------

async def predict_and_publish_async(session: AsyncSession, match_id: int) -> dict:
    round_result = await preds_svc.run_prediction_round(
        session, match_id, cost_guard=_cost_guard(), football=_football()
    )
    await generate_for_match(session, match_id, render_png=True)
    # auto-publish the pre-match cards (Lineup, Contrarian, Bookmaker)
    published = await publish_svc.publish_match(session, match_id, templates=publish_svc.PRE_MATCH)
    return {"action": "predict_and_publish", **round_result, "published": published}


async def lock_async(session: AsyncSession, match_id: int) -> dict:
    return {"action": "lock", **await preds_svc.lock_match(session, match_id)}


async def settle_async(session: AsyncSession, match_id: int, football: FootballClient | None = None) -> dict:
    football = football or _football()
    match = await session.get(Match, match_id)
    if match is None:
        return {"action": "settle", "status": "missing"}

    fx = await football.fixture(match_id)
    if not fx or fx.get("final_score_a") is None:
        return {"action": "settle", "status": "no_result_yet"}

    await ingest_result(session, match_id, fx["final_score_a"], fx["final_score_b"])
    await preds_svc.reveal_match(session, match_id)
    await standings_svc.recompute_standings(session)
    await generate_for_match(session, match_id, render_png=True)
    # auto-publish the post-match cards (Reckoning, Vindication/Faceplant, Receipt)
    published = await publish_svc.publish_match(session, match_id, templates=publish_svc.POST_MATCH)
    return {
        "action": "settle",
        "status": "settled",
        "final": f"{fx['final_score_a']}-{fx['final_score_b']}",
        "published": published,
    }


async def scan_async(session: AsyncSession, now: datetime | None = None) -> list[dict]:
    """Reconcile every match against the clock and return the actions to run."""
    now = now or _now()
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    matches = (await session.execute(select(Match))).scalars().all()

    # which matches already have predictions?
    counts = dict(
        (
            await session.execute(
                select(Prediction.match_id, func.count(Prediction.id)).group_by(Prediction.match_id)
            )
        ).all()
    )

    actions: list[dict] = []
    for m in matches:
        kickoff = m.kickoff_utc
        if kickoff.tzinfo is None:
            kickoff = kickoff.replace(tzinfo=timezone.utc)
        has_preds = counts.get(m.id, 0) > 0

        if not m.locked:
            if now >= kickoff and has_preds:
                # only lock matches we actually predicted; ignore already-played
                # fixtures we never had a prediction window for
                actions.append({"action": "lock", "match_id": m.id})
            elif (kickoff - PREDICT_LEAD) <= now < kickoff and not has_preds:
                # the prediction window is the 4h BEFORE kickoff only — never
                # "predict" a match that has already started or finished
                actions.append({"action": "predict_and_publish", "match_id": m.id})
        elif m.final_score_a is None and now >= kickoff + SETTLE_DELAY:
            actions.append({"action": "settle", "match_id": m.id})
    return actions


# --- session helper ---------------------------------------------------------

def _run(coro_factory):
    async def _wrap():
        async with SessionLocal() as session:
            result = await coro_factory(session)
            await session.commit()
            return result

    return asyncio.run(_wrap())


# --- Celery tasks -----------------------------------------------------------

@celery_app.task(name="app.tasks.jobs.predict_and_publish", bind=True, max_retries=2)
def predict_and_publish(self, match_id: int):
    return _run(lambda s: predict_and_publish_async(s, match_id))


@celery_app.task(name="app.tasks.jobs.lock")
def lock(match_id: int):
    return _run(lambda s: lock_async(s, match_id))


@celery_app.task(name="app.tasks.jobs.settle")
def settle(match_id: int):
    return _run(lambda s: settle_async(s, match_id))


_DISPATCH = {
    "predict_and_publish": predict_and_publish,
    "lock": lock,
    "settle": settle,
}


@celery_app.task(name="app.tasks.jobs.recompute_personalities")
def recompute_personalities():
    """Nightly: refresh the emergent personality badges (BUILD_SPEC §8)."""
    result = _run(lambda s: compute_personalities(s))
    logger.info("personalities: %s", [b["key"] + "->" + b["model"] for b in result["badges"]])
    return result["badges"]


@celery_app.task(name="app.tasks.jobs.scan")
def scan():
    """Beat entrypoint: plan actions, then enqueue the matching task for each."""
    actions = _run(lambda s: scan_async(s))
    for a in actions:
        task = _DISPATCH.get(a["action"])
        if task is not None:
            task.delay(a["match_id"])
    logger.info("scan enqueued %d actions", len(actions))
    return actions
