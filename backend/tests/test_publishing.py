"""Publishing pipeline in dry-run (default) — safe, no credentials, no API calls."""
from __future__ import annotations

from app.content.service import generate_for_match
from app.football.client import FootballClient
from app.publishing import service as publish_svc
from app.publishing.registry import PUBLISH_TARGETS
from app.services import predictions as svc
from app.services.results import ingest_result
from app.services.seed import seed_mock_data

MATCH = 1001


async def _ready(session):
    await seed_mock_data(session, FootballClient())
    await svc.run_prediction_round(session, MATCH, football=FootballClient())
    await svc.lock_match(session, MATCH)
    await svc.reveal_match(session, MATCH)
    await ingest_result(session, MATCH, 2, 1)
    await generate_for_match(session, MATCH, render_png=False)
    await session.commit()


async def test_publish_match_dry_run_marks_posted(sessionmaker):
    async with sessionmaker() as session:
        await _ready(session)
        out = await publish_svc.publish_match(session, MATCH)
        await session.commit()

        assert out["dry_run"] is True
        assert out["total"] > 0
        assert out["posted"] == out["total"]
        # only ever the target platforms, never x
        assert {r["platform"] for r in out["results"]} <= set(PUBLISH_TARGETS)
        assert all(r["dry_run"] for r in out["results"])


async def test_publish_is_idempotent_after_posting(sessionmaker):
    async with sessionmaker() as session:
        await _ready(session)
        await publish_svc.publish_match(session, MATCH)
        await session.commit()
        # rows are now 'posted' (not 'draft'), so a second run finds nothing new
        again = await publish_svc.publish_match(session, MATCH)
        assert again["total"] == 0


async def test_pre_and_post_template_split_no_overlap():
    assert set(publish_svc.PRE_MATCH).isdisjoint(publish_svc.POST_MATCH)
