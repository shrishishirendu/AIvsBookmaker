"""Seed teams + matches from the FootballClient.

Works in both modes: mock fixtures (Phase 0/1) and live API-Football fixtures
(Phase 2). Teams are derived from the fixtures themselves and enriched with our
maintained ratings table (FIFA rank / Elo / form), which the API does not
provide.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from ..football.client import FootballClient
from ..models import Match, Team

_DEFAULT_RATING = {"fifa_rank": 99, "elo": 1500, "gf": 0, "ga": 0, "last5": ""}


def _parse_kickoff(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


async def seed_mock_data(session: AsyncSession, football: FootballClient | None = None) -> dict:
    football = football or FootballClient()

    fixtures = await football.fixtures()
    ratings = football.ratings()

    # collect unique teams from fixtures
    teams: dict[int, str] = {}
    for fx in fixtures:
        if fx.get("team_a_id"):
            teams[fx["team_a_id"]] = fx["team_a"]
        if fx.get("team_b_id"):
            teams[fx["team_b_id"]] = fx["team_b"]

    for team_id, name in teams.items():
        r = {**_DEFAULT_RATING, **ratings.get(name, {})}
        existing = await session.get(Team, team_id)
        if existing is None:
            existing = Team(id=team_id)
            session.add(existing)
        existing.name = name
        existing.fifa_rank = r["fifa_rank"]
        existing.elo = r["elo"]
        existing.gf = r["gf"]
        existing.ga = r["ga"]
        existing.last5 = r["last5"]

    match_ids: list[int] = []
    for fx in fixtures:
        m = await session.get(Match, fx["id"])
        if m is None:
            m = Match(id=fx["id"])
            session.add(m)
        m.team_a = fx["team_a"]
        m.team_b = fx["team_b"]
        m.team_a_id = fx.get("team_a_id")
        m.team_b_id = fx.get("team_b_id")
        m.stage = fx["stage"]
        m.kickoff_utc = _parse_kickoff(fx["kickoff_utc"])
        m.venue = fx.get("venue")
        m.status = fx.get("status", "NS")
        if fx.get("final_score_a") is not None:
            m.final_score_a = fx["final_score_a"]
            m.final_score_b = fx["final_score_b"]
        match_ids.append(fx["id"])

    await session.flush()
    return {"teams": len(teams), "matches": match_ids}
