"""Map API-Football response shapes -> our internal shapes (BUILD_SPEC §3).

API-Football wraps everything in {"response": [...]} with deeply nested objects.
These pure functions flatten that into the compact dicts the rest of the app
consumes, so the real path and the mock path hand the app identical structures.

FIFA rank / Elo are NOT provided by API-Football — those come from our own
maintained ratings table (see FootballClient.ratings). Here we extract what the
API does give: teams, kickoff, venue, status, goals, and match-winner odds.
"""
from __future__ import annotations


def map_fixtures(response: list[dict]) -> list[dict]:
    out = []
    for item in response:
        fx = item.get("fixture", {})
        teams = item.get("teams", {})
        league = item.get("league", {})
        goals = item.get("goals", {})
        home, away = teams.get("home", {}), teams.get("away", {})
        venue = (fx.get("venue") or {})
        venue_str = ", ".join(p for p in [venue.get("name"), venue.get("city")] if p) or None
        out.append(
            {
                "id": fx.get("id"),
                "team_a": home.get("name"),
                "team_b": away.get("name"),
                "team_a_id": home.get("id"),
                "team_b_id": away.get("id"),
                "stage": league.get("round") or league.get("name") or "Group Stage",
                "kickoff_utc": fx.get("date"),
                "venue": venue_str,
                "status": (fx.get("status") or {}).get("short", "NS"),
                "final_score_a": goals.get("home"),
                "final_score_b": goals.get("away"),
            }
        )
    return out


_MATCH_WINNER_BET_NAMES = {"match winner", "1x2", "fulltime result"}


def map_odds(response: list[dict], fixture_id: int) -> list[dict]:
    """Return [{"fixture": id, "books": [{"book","home","draw","away"}]}].

    Pulls the "Match Winner" (1X2) market from every bookmaker in the payload.
    """
    books: list[dict] = []
    for item in response:
        for bm in item.get("bookmakers", []):
            row = _winner_market(bm)
            if row:
                books.append({"book": bm.get("name", "unknown"), **row})
    return [{"fixture": fixture_id, "books": books}] if books else []


def _winner_market(bookmaker: dict) -> dict | None:
    for bet in bookmaker.get("bets", []):
        if bet.get("name", "").strip().lower() in _MATCH_WINNER_BET_NAMES:
            odds = {}
            for v in bet.get("values", []):
                label = str(v.get("value", "")).strip().lower()
                try:
                    odd = float(v.get("odd"))
                except (TypeError, ValueError):
                    continue
                if label in ("home", "1"):
                    odds["home"] = odd
                elif label in ("draw", "x"):
                    odds["draw"] = odd
                elif label in ("away", "2"):
                    odds["away"] = odd
            if {"home", "draw", "away"} <= odds.keys():
                return odds
    return None
