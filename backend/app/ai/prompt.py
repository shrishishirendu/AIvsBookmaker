"""The prompt contract (BUILD_SPEC §4).

Every model gets the EXACT same rendered prompt. Fairness is the brand. The
rendered prompt is stored alongside each prediction and is part of the commit.
"""
from __future__ import annotations

from .base import MatchContext

PROMPT_TEMPLATE = """You are a professional football analyst. Analyze ONE match and predict the result.

MATCH: {team_a} vs {team_b} — {stage}, {kickoff_utc}
{team_a}: FIFA Rank {a_rank} | Elo {a_elo} | Last5 {a_form} | GF {a_gf} GA {a_ga}
{team_b}: FIFA Rank {b_rank} | Elo {b_elo} | Last5 {b_form} | GF {b_gf} GA {b_ga}

Make the `reasoning` SPECIFIC and QUOTABLE — name players, tactics, or matchups
("Algeria's high line dies against Messi's diagonal runs"), never generic
("the stronger team should win").

Return ONLY this JSON, no prose:
{{"winner":"TEAM_A|TEAM_B|DRAW","score_a":int,"score_b":int,"win_probability":0.0-1.0,"reasoning":"one punchy sentence, max 280 chars"}}"""


def render_prompt(ctx: MatchContext) -> str:
    return PROMPT_TEMPLATE.format(
        team_a=ctx.team_a,
        team_b=ctx.team_b,
        stage=ctx.stage,
        kickoff_utc=ctx.kickoff_utc,
        a_rank=ctx.a_rank,
        a_elo=ctx.a_elo,
        a_form=ctx.a_form,
        a_gf=ctx.a_gf,
        a_ga=ctx.a_ga,
        b_rank=ctx.b_rank,
        b_elo=ctx.b_elo,
        b_form=ctx.b_form,
        b_gf=ctx.b_gf,
        b_ga=ctx.b_ga,
    )
