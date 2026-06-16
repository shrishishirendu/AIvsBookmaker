"""Personality badges + tournament highlights."""
from __future__ import annotations

from app.ai.base import MatchPrediction
from app.football.client import FootballClient
from app.services import predictions as svc
from app.services.highlights import compute_highlights
from app.services.personalities import BADGES, compute_personalities
from app.services.results import ingest_result
from app.services.seed import seed_mock_data

MATCH = 1001  # Argentina vs Algeria (mock)


async def _scored_match(session):
    await seed_mock_data(session, FootballClient())
    await svc.run_prediction_round(session, MATCH, football=FootballClient())
    await svc.lock_match(session, MATCH)
    await svc.reveal_match(session, MATCH)
    await ingest_result(session, MATCH, 2, 1)  # Argentina win
    await session.commit()


async def test_personalities_award_known_badges(sessionmaker):
    async with sessionmaker() as session:
        await _scored_match(session)
        out = await compute_personalities(session)

        keys = {b["key"] for b in out["badges"]}
        # Quant always awarded once there's data; all badge keys are valid
        assert "quant" in keys
        assert keys <= set(BADGES)
        # every badge points at a real model with a value string
        for b in out["badges"]:
            assert b["model"] in {m["model"] for m in out["models"]}
            assert b["value"]


async def test_personalities_empty_without_results(sessionmaker):
    async with sessionmaker() as session:
        await seed_mock_data(session, FootballClient())
        await svc.run_prediction_round(session, MATCH, football=FootballClient())
        await session.commit()  # predicted but no result -> nothing scored
        out = await compute_personalities(session)
        assert out["badges"] == []


async def test_highlights_lists_calls_and_misses(sessionmaker):
    async with sessionmaker() as session:
        await _scored_match(session)
        out = await compute_highlights(session)
        assert "best_calls" in out and "worst_misses" in out and "upsets" in out
        # best call should be the top-scoring competitor for the match
        assert out["best_calls"]
        assert out["best_calls"][0]["points"] >= out["best_calls"][-1]["points"]
