"""Public user predictions + the persisted 3-way leaderboard."""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.ai.base import MatchPrediction
from app.football.client import FootballClient
from app.models import Prediction
from app.services import predictions as svc
from app.services import standings as standings_svc
from app.services.results import ingest_result
from app.services.seed import seed_mock_data

MATCH_ID = 1001


async def _seed_and_predict(session):
    await seed_mock_data(session, FootballClient())
    await svc.run_prediction_round(session, MATCH_ID, football=FootballClient())
    await session.commit()


async def test_user_prediction_uses_commit_reveal(sessionmaker):
    async with sessionmaker() as session:
        await _seed_and_predict(session)
        pick = MatchPrediction(
            winner="TEAM_A", score_a=2, score_b=1, win_probability=0.8,
            reasoning="My gut says Messi runs the show.",
        )
        out = await svc.submit_user_prediction(session, MATCH_ID, "@fan_42", pick)
        await session.commit()
        assert out["competitor"] == "user:fan_42"
        assert len(out["commit_hash"]) == 64

        # the user's committed pick verifies against its hash like any other
        pred_id = (
            await session.execute(
                select(Prediction.id).where(Prediction.competitor == "user:fan_42")
            )
        ).scalar_one()
        await svc.reveal_match(session, MATCH_ID)
        await session.commit()
        v = await svc.verify_prediction(session, pred_id)
        assert v["match"] is True
        assert v["competitor"] == "user:fan_42"


async def test_user_prediction_blocked_after_lock(sessionmaker):
    async with sessionmaker() as session:
        await _seed_and_predict(session)
        await svc.lock_match(session, MATCH_ID)
        await session.commit()
        with pytest.raises(svc.LockedError):
            await svc.submit_user_prediction(
                session, MATCH_ID, "late_user",
                MatchPrediction(winner="DRAW", score_a=1, score_b=1,
                                win_probability=0.4, reasoning="too late"),
            )


async def test_leaderboard_three_tiers(sessionmaker):
    async with sessionmaker() as session:
        await _seed_and_predict(session)
        # two members of the public lock picks
        await svc.submit_user_prediction(
            session, MATCH_ID, "alice",
            MatchPrediction(winner="TEAM_A", score_a=2, score_b=1, win_probability=0.7, reasoning="x"))
        await svc.submit_user_prediction(
            session, MATCH_ID, "bob",
            MatchPrediction(winner="TEAM_B", score_a=0, score_b=1, win_probability=0.6, reasoning="y"))
        await svc.lock_match(session, MATCH_ID)
        await svc.reveal_match(session, MATCH_ID)
        await ingest_result(session, MATCH_ID, 2, 1)  # Argentina win, alice nails exact
        await standings_svc.recompute_standings(session)
        await session.commit()

        board = await standings_svc.leaderboard(session, "overall")
        tiers = {row["tier"] for row in board}
        assert {"ai", "bookmaker", "user", "public"} <= tiers

        by_comp = {row["competitor"]: row for row in board}
        # alice predicted exact 2-1 -> 3 + 5 + 2 + 2(team goals) = 12, tops the table
        assert by_comp["user:alice"]["points"] == 12
        assert board[0]["points"] == 12


async def test_leaderboard_rejects_bad_scope(sessionmaker):
    async with sessionmaker() as session:
        await _seed_and_predict(session)
        with pytest.raises(ValueError):
            await standings_svc.leaderboard(session, "daily")
