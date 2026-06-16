"""API-Football response mappers -> internal shapes."""
from __future__ import annotations

import json
from pathlib import Path

from app.football.mappers import map_fixtures, map_odds
from app.football.odds import consensus_from_books

RAW = Path(__file__).resolve().parents[1] / "mock" / "raw"


def _load(name):
    return json.loads((RAW / name).read_text(encoding="utf-8"))


def test_map_fixtures_flattens_nested_shape():
    out = map_fixtures(_load("fixtures_raw.json"))
    assert len(out) == 2
    a = out[0]
    assert a["id"] == 1001
    assert a["team_a"] == "Argentina" and a["team_b"] == "Algeria"
    assert a["team_a_id"] == 26 and a["team_b_id"] == 1531
    assert a["stage"] == "Group A"
    assert a["kickoff_utc"].startswith("2026-06-13")
    assert a["venue"] == "Estadio Azteca, Mexico City"
    assert a["status"] == "FT"
    assert a["final_score_a"] == 2 and a["final_score_b"] == 1
    # unfinished match has null goals
    assert out[1]["final_score_a"] is None


def test_map_odds_extracts_match_winner_market():
    out = map_odds(_load("odds_raw.json"), 1001)
    assert len(out) == 1
    entry = out[0]
    assert entry["fixture"] == 1001
    assert len(entry["books"]) == 2
    books = {b["book"]: b for b in entry["books"]}
    assert books["Bet365"]["home"] == 1.33
    assert books["Pinnacle"]["away"] == 9.50
    # the mapped books feed straight into the de-vig consensus
    consensus = consensus_from_books(entry["books"])
    assert consensus.overround > 1.0
    assert abs((consensus.home_pct + consensus.draw_pct + consensus.away_pct) - 1.0) < 1e-9


def test_map_odds_empty_when_no_market():
    assert map_odds([{"fixture": {"id": 9}, "bookmakers": []}], 9) == []
