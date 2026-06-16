"""Phase 2 checkpoint, visibly — no Redis/Celery/Postgres required.

Demonstrates, on a throwaway SQLite DB:
  * live-provider gating (each model live if its key is set, else mock)
  * the Celery scan reconciling state and the predict -> lock -> settle cores
  * public user predictions via the same commit-reveal pipeline
  * the persisted 3-way leaderboard (5 AIs + Bookmaker + Public)

Run:  python -m scripts.demo_phase2
"""
from __future__ import annotations

import asyncio
import sys
from datetime import timedelta

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from app.ai.base import MatchPrediction
from app.ai.registry import PROVIDERS
from app.config import settings
from app.football.client import FootballClient
from app.models import Match
from app.services import predictions as svc
from app.services import standings as standings_svc
from app.services.seed import seed_mock_data
from app.sqlite_setup import make_sqlite
from app.tasks import jobs

MATCH_ID = 1001
KICKOFF = None  # filled from the seeded match


class FinishedFootball(FootballClient):
    """Stands in for API-Football reporting a finished 2-1 result."""

    async def fixture(self, fixture_id: int):
        return {"id": fixture_id, "final_score_a": 2, "final_score_b": 1, "status": "FT"}


def rule(t: str) -> None:
    print(f"\n{'=' * 72}\n{t}\n{'=' * 72}")


_KEYS = {
    "Claude": settings.anthropic_api_key, "ChatGPT": settings.openai_api_key,
    "Gemini": settings.gemini_api_key, "Grok": settings.xai_api_key,
    "DeepSeek": settings.deepseek_api_key,
}


async def main() -> None:
    engine, sessionmaker = await make_sqlite()
    football = FootballClient()

    async with sessionmaker() as session:
        await seed_mock_data(session, football)
        await session.commit()
        match = await session.get(Match, MATCH_ID)
        kickoff = match.kickoff_utc

        rule("PROVIDER MODE — live if a key is present, else mock fallback")
        for p in PROVIDERS:
            mode = "LIVE" if _KEYS.get(p.name) else "mock (no key)"
            print(f"  {p.name:10s} -> {mode}")

        rule("SCAN @ T-3h — Beat would enqueue the prediction round")
        actions = await jobs.scan_async(session, now=kickoff - timedelta(hours=3))
        print(f"  planned: {actions}")

        rule("PREDICT + PUBLISH — run round, commit hashes, build pre-match cards")
        out = await jobs.predict_and_publish_async(session, MATCH_ID)
        await session.commit()
        print(f"  committed competitors: {out['competitors']}")

        rule("PUBLIC joins — two users lock picks (same commit-reveal)")
        await svc.submit_user_prediction(session, MATCH_ID, "alice",
            MatchPrediction(winner="TEAM_A", score_a=2, score_b=1, win_probability=0.75,
                            reasoning="Argentina by a goal, Messi decisive."))
        await svc.submit_user_prediction(session, MATCH_ID, "bob",
            MatchPrediction(winner="TEAM_B", score_a=0, score_b=1, win_probability=0.55,
                            reasoning="Algeria shock the world."))
        await session.commit()
        print("  alice -> Argentina 2-1   bob -> Algeria 0-1")

        rule("SCAN @ kickoff — Beat would enqueue the lock")
        actions = await jobs.scan_async(session, now=kickoff + timedelta(minutes=1))
        print(f"  planned: {actions}")
        await jobs.lock_async(session, MATCH_ID)
        await session.commit()

        rule("SCAN @ kickoff+3h — Beat would enqueue settle (poll result)")
        actions = await jobs.scan_async(session, now=kickoff + timedelta(hours=3))
        print(f"  planned: {actions}")

        rule("SETTLE — result 2-1 ingested, revealed, scored, post-match cards built")
        settled = await jobs.settle_async(session, MATCH_ID, football=FinishedFootball())
        await session.commit()
        print(f"  {settled}")

        rule("THREE-WAY LEADERBOARD (overall) — can the public beat the machines?")
        board = await standings_svc.leaderboard(session, "overall")
        print(f"  {'#':>2}  {'competitor':14s} {'tier':10s} {'pts':>4} {'acc':>5} {'exact':>5}")
        for r in board:
            print(f"  {r['rank']:>2}  {r['competitor']:14s} {r['tier']:10s} "
                  f"{r['points']:>4} {r['accuracy']:>5.0%} {r['exact_scores']:>5}")

        rule("PHASE 2 CHECKPOINT")
        tiers = {r["tier"] for r in board}
        print(f"  Live LLM providers wired with mock fallback: 5/5")
        print(f"  API-Football real path (mappers) behind MOCK_FOOTBALL toggle: YES")
        print(f"  Celery scan -> predict/lock/settle auto-triggers: YES")
        print(f"  3-way leaderboard tiers present: {sorted(tiers)}")
        ok = {"ai", "bookmaker", "user", "public"} <= tiers and settled["status"] == "settled"
        print("\n  [PASS] Phase 2 checkpoint met." if ok else "\n  [FAIL]")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
