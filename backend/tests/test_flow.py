"""Phase 0 checkpoint as an automated test:
one mock match flows predict -> commit -> lock -> reveal, and /verify is true.
Also proves the DB-level lock trigger refuses to mutate a locked prediction.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.football.client import FootballClient
from app.models import Match, Prediction
from app.services import predictions as svc

MATCH_ID = 1001  # Argentina vs Algeria, from the mock fixtures


async def _seed(session):
    from app.services.seed import seed_mock_data

    await seed_mock_data(session, FootballClient())
    await session.commit()


async def test_full_commit_reveal_flow(sessionmaker):
    async with sessionmaker() as session:
        await _seed(session)

        # PREDICT + COMMIT — 5 models + bookmaker, hashes published, plaintext sealed
        result = await svc.run_prediction_round(session, MATCH_ID, football=FootballClient())
        await session.commit()

        assert "bookmaker" in result["competitors"]
        assert len([c for c in result["competitors"] if c != "bookmaker"]) == 5

        preds = (
            await session.execute(select(Prediction).where(Prediction.match_id == MATCH_ID))
        ).scalars().all()
        assert len(preds) == 6
        assert all(p.commit_hash and p.committed_at for p in preds)
        assert all(p.revealed is False for p in preds)  # sealed before reveal

        # LOCK
        await svc.lock_match(session, MATCH_ID)
        await session.commit()
        match = await session.get(Match, MATCH_ID)
        assert match.locked is True and match.locked_at is not None

        # REVEAL — only the `revealed` flag flips
        await svc.reveal_match(session, MATCH_ID)
        await session.commit()

        # VERIFY — every revealed prediction re-hashes to its commit
        for p in preds:
            v = await svc.verify_prediction(session, p.id)
            assert v["match"] is True, f"{p.competitor} failed verification"
            assert v["revealed"] is True
            assert v["prediction"] is not None


async def test_db_trigger_blocks_locked_payload_edit(sessionmaker):
    async with sessionmaker() as session:
        await _seed(session)
        await svc.run_prediction_round(session, MATCH_ID, football=FootballClient())
        await session.commit()
        await svc.lock_match(session, MATCH_ID)
        await session.commit()

        pred = (
            await session.execute(select(Prediction).where(Prediction.match_id == MATCH_ID))
        ).scalars().first()

        # Attempting to rewrite the payload of a locked prediction must be
        # rejected by the DATABASE, not just app code.
        pred.score_a = pred.score_a + 99
        with pytest.raises(Exception) as exc:
            await session.flush()
        assert "locked" in str(exc.value).lower()
        await session.rollback()


async def test_predict_blocked_after_lock(sessionmaker):
    async with sessionmaker() as session:
        await _seed(session)
        await svc.run_prediction_round(session, MATCH_ID, football=FootballClient())
        await session.commit()
        await svc.lock_match(session, MATCH_ID)
        await session.commit()

        with pytest.raises(svc.LockedError):
            await svc.run_prediction_round(session, MATCH_ID, football=FootballClient())
