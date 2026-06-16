"""Celery task async-cores: scan reconciliation + settle, no broker needed."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.football.client import FootballClient
from app.models import Match, Prediction
from app.services import predictions as svc
from app.services.seed import seed_mock_data
from app.tasks import jobs

MATCH_ID = 1001
KICKOFF = datetime(2026, 6, 13, 19, 0, tzinfo=timezone.utc)


async def _seed(session):
    await seed_mock_data(session, FootballClient())
    await session.commit()


async def test_scan_plans_predict_then_lock_then_settle(sessionmaker):
    async with sessionmaker() as session:
        await _seed(session)

        # 5 hours before kickoff: nothing yet (outside the T-4h window)
        actions = await jobs.scan_async(session, now=KICKOFF - timedelta(hours=5))
        assert all(a["action"] != "predict_and_publish" or a["match_id"] != MATCH_ID for a in actions)

        # 3 hours before kickoff: predict_and_publish is planned
        actions = await jobs.scan_async(session, now=KICKOFF - timedelta(hours=3))
        assert {"action": "predict_and_publish", "match_id": MATCH_ID} in actions

        # after predictions exist + past kickoff: plan is to lock
        await svc.run_prediction_round(session, MATCH_ID, football=FootballClient())
        await session.commit()
        actions = await jobs.scan_async(session, now=KICKOFF + timedelta(minutes=1))
        assert {"action": "lock", "match_id": MATCH_ID} in actions

        # locked, 3h after kickoff, no result: plan is to settle
        await svc.lock_match(session, MATCH_ID)
        await session.commit()
        actions = await jobs.scan_async(session, now=KICKOFF + timedelta(hours=3))
        assert {"action": "settle", "match_id": MATCH_ID} in actions


class _FinishedFootball(FootballClient):
    """Football client whose fixture endpoint reports a finished match."""

    async def fixture(self, fixture_id: int):
        return {"id": fixture_id, "final_score_a": 2, "final_score_b": 1, "status": "FT"}


async def test_settle_ingests_reveals_scores_and_builds_content(sessionmaker):
    async with sessionmaker() as session:
        await _seed(session)
        await svc.run_prediction_round(session, MATCH_ID, football=FootballClient())
        await svc.lock_match(session, MATCH_ID)
        await session.commit()

        out = await jobs.settle_async(session, MATCH_ID, football=_FinishedFootball())
        await session.commit()
        assert out["status"] == "settled"
        assert out["final"] == "2-1"

        match = await session.get(Match, MATCH_ID)
        assert match.final_score_a == 2 and match.final_score_b == 1

        # every prediction is revealed and scored
        preds = (
            await session.execute(select(Prediction).where(Prediction.match_id == MATCH_ID))
        ).scalars().all()
        assert all(p.revealed for p in preds)
        assert all(p.points_awarded is not None for p in preds)


async def test_settle_waits_when_no_result(sessionmaker):
    async with sessionmaker() as session:
        await _seed(session)
        await svc.run_prediction_round(session, MATCH_ID, football=FootballClient())
        await svc.lock_match(session, MATCH_ID)
        await session.commit()
        # default mock fixtures have no final score
        out = await jobs.settle_async(session, MATCH_ID, football=FootballClient())
        assert out["status"] == "no_result_yet"
