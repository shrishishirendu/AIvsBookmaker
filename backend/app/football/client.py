"""Thin API-Football client with the same mock/real toggle as the AI layer.

Phase 0 runs MOCK_FOOTBALL=true and serves fixtures from backend/mock/.
Phase 2 flips the toggle; the real path caches fixture + odds responses in Redis
(TTL 10 min) because API-Football rate-limits hard.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import httpx

from ..config import settings
from .mappers import map_fixtures, map_odds

logger = logging.getLogger(__name__)

BASE_URL = "https://v3.football.api-sports.io"
MOCK_DIR = Path(__file__).resolve().parents[2] / "mock"
CACHE_TTL = 600  # seconds


class FootballClient:
    def __init__(self, redis_client=None):
        self._redis = redis_client

    # --- public API ---------------------------------------------------------

    async def fixtures(self, league: int | None = None, season: int | None = None) -> list[dict]:
        league = league if league is not None else settings.football_league
        season = season if season is not None else settings.football_season
        data = await self._get(
            "/fixtures",
            params={"league": league, "season": season},
            mock_file="fixtures.json",
        )
        return map_fixtures(data) if not settings.mock_football else data

    async def fixture(self, fixture_id: int) -> dict | None:
        data = await self._get(
            "/fixtures",
            params={"id": fixture_id},
            mock_file="fixtures.json",
        )
        fixtures = map_fixtures(data) if not settings.mock_football else data
        for fx in fixtures:
            if fx.get("id") == fixture_id:
                return fx
        return None

    async def odds(self, fixture_id: int) -> list[dict]:
        data = await self._get(
            "/odds",
            params={"fixture": fixture_id},
            mock_file="odds.json",
        )
        if not settings.mock_football:
            return map_odds(data, fixture_id)
        return [o for o in data if o.get("fixture") == fixture_id] or data

    async def team_statistics(self) -> list[dict]:
        return await self._get("/teams/statistics", params={}, mock_file="teams.json")

    def ratings(self) -> dict[str, dict]:
        """Maintained FIFA-rank / Elo table, keyed by team name.

        API-Football does not expose FIFA rank or Elo, so we keep our own. Used
        to enrich fixture-derived teams in both mock and live modes.
        """
        path = MOCK_DIR / "ratings.json"
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)

    # --- internals ----------------------------------------------------------

    async def _get(self, path: str, params: dict, mock_file: str) -> list[dict]:
        if settings.mock_football:
            return self._load_mock(mock_file)

        cache_key = f"apifootball:{path}:{json.dumps(params, sort_keys=True)}"
        cached = await self._cache_get(cache_key)
        if cached is not None:
            return cached

        if not settings.apifootball_key:
            logger.warning("APIFOOTBALL_KEY unset and MOCK_FOOTBALL=false; using mock")
            return self._load_mock(mock_file)

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{BASE_URL}{path}",
                params=params,
                headers={"x-apisports-key": settings.apifootball_key},
            )
            resp.raise_for_status()
            payload = resp.json()
        # API-Football wraps results in {"response": [...]}.
        data = payload.get("response", payload) if isinstance(payload, dict) else payload
        await self._cache_set(cache_key, data)
        return data

    def _load_mock(self, mock_file: str) -> list[dict]:
        path = MOCK_DIR / mock_file
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)

    async def _cache_get(self, key: str):
        if self._redis is None:
            return None
        try:
            raw = await self._redis.get(key)
            return json.loads(raw) if raw else None
        except Exception as exc:  # pragma: no cover
            logger.warning("football cache read failed: %s", exc)
            return None

    async def _cache_set(self, key: str, value) -> None:
        if self._redis is None:
            return
        try:
            await self._redis.set(key, json.dumps(value), ex=CACHE_TTL)
        except Exception as exc:  # pragma: no cover
            logger.warning("football cache write failed: %s", exc)
