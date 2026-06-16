"""End-to-end content generation against SQLite (no browser needed)."""
from __future__ import annotations

from app.content.service import generate_for_match, get_content
from app.content.tone import PLATFORMS
from app.football.client import FootballClient
from app.services import predictions as svc
from app.services.results import ingest_result
from app.services.seed import seed_mock_data

MATCH_ID = 1001


async def _prepared(session):
    await seed_mock_data(session, FootballClient())
    await svc.run_prediction_round(session, MATCH_ID, football=FootballClient())
    await svc.lock_match(session, MATCH_ID)
    await svc.reveal_match(session, MATCH_ID)
    await session.commit()


async def test_pre_match_content(sessionmaker):
    async with sessionmaker() as session:
        await _prepared(session)
        out = await generate_for_match(session, MATCH_ID, render_png=False)
        await session.commit()

        by_t = {c["template"]: c for c in out["generated"]}
        # the 4 pre/always templates exist; post-match ones require a result
        assert {"lineup_card", "contrarian", "bookmaker_challenge", "receipt"} <= by_t.keys()
        assert "reckoning" not in by_t

        # Grok is the lone dissenter in the mock data -> contrarian fires
        assert by_t["contrarian"]["triggered"] is True

        # every template produced a caption for every platform, X within limit
        for c in out["generated"]:
            assert set(c["captions"].keys()) == set(PLATFORMS)
            assert len(c["captions"]["x"]) <= 280
            assert c["html_url"].endswith(".html")


async def test_post_match_content_after_result(sessionmaker):
    async with sessionmaker() as session:
        await _prepared(session)
        # Argentina 2-1 Algeria -> Claude (predicted 2-1) is the hero
        await ingest_result(session, MATCH_ID, 2, 1)
        await session.commit()

        out = await generate_for_match(session, MATCH_ID, render_png=False)
        await session.commit()
        by_t = {c["template"]: c for c in out["generated"]}

        assert "reckoning" in by_t
        assert "vindication_faceplant" in by_t
        assert by_t["vindication_faceplant"]["triggered"] is True

        # persisted + retrievable
        stored = await get_content(session, MATCH_ID)
        templates = {c["template"] for c in stored["content"]}
        assert "vindication_faceplant" in templates
