"""Trigger logic: contrarian detection + bookmaker divergence."""
from __future__ import annotations

from app.content.models import Pick
from app.content.triggers import (
    ai_consensus,
    bookmaker_challenge,
    detect_contrarian,
)


def _pick(comp, winner, conf=0.6):
    return Pick(comp, winner, 1, 0, conf, "x", "h", True)


def test_contrarian_fires_on_single_dissenter():
    picks = [
        _pick("Claude", "TEAM_A"),
        _pick("ChatGPT", "TEAM_A"),
        _pick("Gemini", "TEAM_A"),
        _pick("DeepSeek", "TEAM_A"),
        _pick("Grok", "TEAM_B"),
    ]
    res = detect_contrarian(picks)
    assert res.triggered
    assert res.dissenter == "Grok"
    assert res.dissent_winner == "TEAM_B"
    assert res.majority_winner == "TEAM_A"
    assert res.majority_count == 4


def test_contrarian_silent_when_two_dissent():
    picks = [
        _pick("Claude", "TEAM_A"),
        _pick("ChatGPT", "TEAM_A"),
        _pick("Gemini", "TEAM_A"),
        _pick("DeepSeek", "TEAM_B"),
        _pick("Grok", "TEAM_B"),
    ]
    assert detect_contrarian(picks).triggered is False


def test_contrarian_silent_on_unanimous():
    picks = [_pick(c, "TEAM_A") for c in ("Claude", "ChatGPT", "Gemini", "Grok", "DeepSeek")]
    assert detect_contrarian(picks).triggered is False


def test_consensus_picks_majority_and_averages_backers():
    picks = [
        _pick("Claude", "TEAM_A", 0.70),
        _pick("ChatGPT", "TEAM_A", 0.60),
        _pick("Grok", "TEAM_B", 0.90),  # not a backer of TEAM_A
    ]
    c = ai_consensus(picks)
    assert c.winner == "TEAM_A"
    assert c.agree_count == 2
    assert abs(c.avg_confidence - 0.65) < 1e-9  # ignores Grok


def test_bookmaker_challenge_fires_past_threshold():
    picks = [_pick(c, "TEAM_A", 0.85) for c in ("Claude", "ChatGPT", "Gemini")]
    # AI ~85%, book home 50% -> 35pp gap -> fires
    res = bookmaker_challenge(picks, home_pct=0.50, draw_pct=0.30, away_pct=0.20)
    assert res.triggered
    assert res.outcome == "TEAM_A"
    assert round(res.diff_pp) == 35


def test_bookmaker_challenge_quiet_when_aligned():
    picks = [_pick(c, "TEAM_A", 0.55) for c in ("Claude", "ChatGPT", "Gemini")]
    res = bookmaker_challenge(picks, home_pct=0.52, draw_pct=0.28, away_pct=0.20)
    assert res.triggered is False
