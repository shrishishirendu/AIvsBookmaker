"""The six content templates (BUILD_SPEC §7).

Each builder is a pure function of (match, predictions, result?) and returns a
template payload:

    {
      "template": str,
      "title": str,            # human label for the admin
      "triggered": bool,       # did its auto-post condition fire?
      "width": int, "height": int,
      "image_spec": {...},     # everything cards.py needs to render
      "facts": {...},          # normalized facts tone.py turns into captions
    }

The image is rendered separately (cards.py + a headless screenshot); the caption
is generated separately (tone.py). Nothing here knows about HTML or platforms.
"""
from __future__ import annotations

from .models import COMPETITOR_COLORS, ConsensusView, MatchView, Pick
from .triggers import (
    ai_consensus,
    bookmaker_challenge,
    detect_contrarian,
)

PORTRAIT = (1080, 1350)  # Instagram portrait — the house dimensions


def _color(competitor: str) -> str:
    return COMPETITOR_COLORS.get(competitor, "#9ca3af")


def _score_str(p: Pick) -> str:
    return f"{p.score_a}-{p.score_b}"


def _pick_str(p: Pick, team_a: str, team_b: str) -> str:
    if p.winner == "DRAW":
        return f"Draw {p.score_a}-{p.score_b}"
    return f"{p.team(team_a, team_b)} {p.score_a}-{p.score_b}"


def _outcome_team(outcome: str, team_a: str, team_b: str) -> str:
    return {"TEAM_A": team_a, "TEAM_B": team_b, "DRAW": "Draw"}[outcome]


# --- 1. The Lineup Card (always) -------------------------------------------

def build_lineup_card(match: MatchView, ai_picks: list[Pick], book: Pick | None) -> dict:
    rows = [
        {
            "competitor": p.competitor,
            "color": _color(p.competitor),
            "team": p.team(match.team_a, match.team_b),
            "score": _score_str(p),
            "confidence": round(p.win_probability * 100),
            "reasoning": p.reasoning,
        }
        for p in ai_picks
    ]
    house = None
    if book is not None:
        house = {
            "team": book.team(match.team_a, match.team_b),
            "score": _score_str(book),
            "confidence": round(book.win_probability * 100),
        }
    return {
        "template": "lineup_card",
        "title": "The Lineup Card",
        "triggered": True,
        "width": PORTRAIT[0],
        "height": PORTRAIT[1],
        "image_spec": {
            "team_a": match.team_a,
            "team_b": match.team_b,
            "stage": match.stage,
            "kickoff_utc": match.kickoff_utc,
            "picks": rows,
            "house": house,
        },
        "facts": {
            "kind": "lineup",
            "team_a": match.team_a,
            "team_b": match.team_b,
            "stage": match.stage,
            "picks": [{"competitor": r["competitor"], "team": r["team"],
                       "confidence": r["confidence"]} for r in rows],
            "house": house,
        },
    }


# --- 2. The Contrarian Spotlight (1 dissenter) ------------------------------

def build_contrarian(match: MatchView, ai_picks: list[Pick]) -> dict:
    res = detect_contrarian(ai_picks)
    dissent_team = majority_team = None
    if res.triggered:
        dissent_team = _outcome_team(res.dissent_winner, match.team_a, match.team_b)
        majority_team = _outcome_team(res.majority_winner, match.team_a, match.team_b)
    dissenter_pick = next(
        (p for p in ai_picks if p.competitor == res.dissenter), None
    ) if res.triggered else None
    return {
        "template": "contrarian",
        "title": "The Contrarian Spotlight",
        "triggered": res.triggered,
        "width": PORTRAIT[0],
        "height": PORTRAIT[1],
        "image_spec": {
            "team_a": match.team_a,
            "team_b": match.team_b,
            "dissenter": res.dissenter,
            "dissenter_color": _color(res.dissenter) if res.dissenter else "#9ca3af",
            "dissent_team": dissent_team,
            "majority_team": majority_team,
            "majority_count": res.majority_count,
            "reasoning": dissenter_pick.reasoning if dissenter_pick else None,
        },
        "facts": {
            "kind": "contrarian",
            "dissenter": res.dissenter,
            "dissent_team": dissent_team,
            "majority_team": majority_team,
            "majority_count": res.majority_count,
        },
    }


# --- 3. The Bookmaker Challenge (>15pp divergence) --------------------------

def build_bookmaker_challenge(
    match: MatchView, ai_picks: list[Pick], consensus: ConsensusView | None
) -> dict:
    triggered = False
    outcome_team = None
    ai_pct = book_pct = diff = 0.0
    if consensus is not None:
        res = bookmaker_challenge(
            ai_picks, consensus.home_pct, consensus.draw_pct, consensus.away_pct
        )
        if res is not None:
            triggered = res.triggered
            outcome_team = _outcome_team(res.outcome, match.team_a, match.team_b)
            ai_pct, book_pct, diff = res.ai_pct, res.book_pct, res.diff_pp
    return {
        "template": "bookmaker_challenge",
        "title": "The Bookmaker Challenge",
        "triggered": triggered,
        "width": PORTRAIT[0],
        "height": PORTRAIT[1],
        "image_spec": {
            "team_a": match.team_a,
            "team_b": match.team_b,
            "outcome_team": outcome_team,
            "ai_pct": round(ai_pct),
            "book_pct": round(book_pct),
            "diff_pp": round(diff),
        },
        "facts": {
            "kind": "bookmaker",
            "outcome_team": outcome_team,
            "ai_pct": round(ai_pct),
            "book_pct": round(book_pct),
            "diff_pp": round(diff),
        },
    }


# --- 4. The Reckoning (post: standings delta) -------------------------------

def build_reckoning(match: MatchView, standings_delta: list[dict]) -> dict:
    """`standings_delta` rows: {competitor, points_delta, total_points, rank, rank_delta}."""
    rows = [
        {**r, "color": _color(r["competitor"])}
        for r in standings_delta
    ]
    return {
        "template": "reckoning",
        "title": "The Reckoning",
        "triggered": match.has_result,
        "width": PORTRAIT[0],
        "height": PORTRAIT[1],
        "image_spec": {
            "team_a": match.team_a,
            "team_b": match.team_b,
            "final": f"{match.final_score_a}-{match.final_score_b}" if match.has_result else None,
            "rows": rows,
        },
        "facts": {
            "kind": "reckoning",
            "rows": [{"competitor": r["competitor"], "rank": r["rank"],
                      "rank_delta": r["rank_delta"], "points_delta": r["points_delta"]}
                     for r in rows],
        },
    }


# --- 5. The Vindication / The Faceplant (post: hero + villain) --------------

def build_vindication_faceplant(
    match: MatchView, ai_picks: list[Pick], book: Pick | None
) -> dict:
    triggered = match.has_result
    everyone = ai_picks + ([book] if book else [])
    scored = [p for p in everyone if p.points_awarded is not None]

    def _card(p, label):
        return {
            "competitor": p.competitor,
            "color": _color(p.competitor),
            "label": label,
            "pick": _pick_str(p, match.team_a, match.team_b),
            "points": p.points_awarded,
            "confidence": round(p.win_probability * 100),
            "reasoning": p.reasoning,
        }

    hero = villain = None
    if scored:
        correct = [p for p in scored if p.winner == match.actual_outcome]
        wrong = [p for p in scored if p.winner != match.actual_outcome]

        # Villain: the most confident wrong call; if everyone was right, fewest points.
        villain_pick = (max(wrong, key=lambda p: p.win_probability) if wrong
                        else min(scored, key=lambda p: p.points_awarded))

        # Hero: top scorer if anyone scored points; otherwise the "least wrong"
        # (lowest-confidence miss) so we never crown the same model twice.
        if correct:
            hero_pick = max(correct, key=lambda p: (p.points_awarded, p.win_probability))
            hero_label = "THE VINDICATION"
        else:
            hero_pick = min(scored, key=lambda p: p.win_probability)
            hero_label = "THE LEAST WRONG"

        # Guarantee hero != villain when more than one competitor was scored.
        if hero_pick.competitor == villain_pick.competitor and len(scored) > 1:
            others = [p for p in scored if p.competitor != villain_pick.competitor]
            pool = [p for p in correct if p.competitor != villain_pick.competitor] or others
            hero_pick = (max(pool, key=lambda p: (p.points_awarded, p.win_probability))
                         if correct else min(pool, key=lambda p: p.win_probability))

        hero = _card(hero_pick, hero_label)
        villain = _card(villain_pick, "THE FACEPLANT")

    return {
        "template": "vindication_faceplant",
        "title": "The Vindication / The Faceplant",
        "triggered": triggered,
        "width": PORTRAIT[0],
        "height": PORTRAIT[1],
        "image_spec": {
            "team_a": match.team_a,
            "team_b": match.team_b,
            "final": f"{match.final_score_a}-{match.final_score_b}" if match.has_result else None,
            "hero": hero,
            "villain": villain,
        },
        "facts": {
            "kind": "vindication",
            "final": f"{match.final_score_a}-{match.final_score_b}" if match.has_result else None,
            "hero": hero,
            "villain": villain,
        },
    }


# --- 6. The Receipt (commit -> reveal -> verified) --------------------------

def build_receipt(match: MatchView, all_picks: list[Pick], verify_fn) -> dict:
    """`verify_fn(pick) -> bool` recomputes the hash from the revealed plaintext."""
    rows = []
    for p in all_picks:
        verified = verify_fn(p) if p.revealed else None
        rows.append(
            {
                "competitor": p.competitor,
                "color": _color(p.competitor),
                "commit_hash": p.commit_hash,
                "revealed": p.revealed,
                "pick": _pick_str(p, match.team_a, match.team_b) if p.revealed else None,
                "verified": verified,
            }
        )
    any_revealed = any(r["revealed"] for r in rows)
    return {
        "template": "receipt",
        "title": "The Receipt",
        "triggered": True,
        "width": PORTRAIT[0],
        "height": PORTRAIT[1],
        "image_spec": {
            "team_a": match.team_a,
            "team_b": match.team_b,
            "stage": match.stage,
            "revealed": any_revealed,
            "rows": rows,
        },
        "facts": {
            "kind": "receipt",
            "team_a": match.team_a,
            "team_b": match.team_b,
            "revealed": any_revealed,
            "verified_count": sum(1 for r in rows if r["verified"]),
            "total": len(rows),
        },
    }
