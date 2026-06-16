"""initial schema + prediction lock trigger

Revision ID: 0001
Revises:
Create Date: 2026-06-16
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.db_triggers import POSTGRES_UP, POSTGRES_DOWN

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False, unique=True),
        sa.Column("fifa_rank", sa.Integer(), nullable=False),
        sa.Column("elo", sa.Integer(), nullable=False),
        sa.Column("gf", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ga", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last5", sa.String(10), nullable=False, server_default=""),
    )

    op.create_table(
        "matches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("team_a", sa.String(80), nullable=False),
        sa.Column("team_b", sa.String(80), nullable=False),
        sa.Column("team_a_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("team_b_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("stage", sa.String(40), nullable=False),
        sa.Column("kickoff_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("venue", sa.String(120), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="NS"),
        sa.Column("degraded", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("locked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("final_score_a", sa.Integer(), nullable=True),
        sa.Column("final_score_b", sa.Integer(), nullable=True),
    )

    op.create_table(
        "odds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id"), nullable=False),
        sa.Column("book", sa.String(40), nullable=False),
        sa.Column("home", sa.Float(), nullable=False),
        sa.Column("draw", sa.Float(), nullable=False),
        sa.Column("away", sa.Float(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "consensus_odds",
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id"), primary_key=True),
        sa.Column("home_pct", sa.Float(), nullable=False),
        sa.Column("draw_pct", sa.Float(), nullable=False),
        sa.Column("away_pct", sa.Float(), nullable=False),
        sa.Column("overround", sa.Float(), nullable=False),
    )

    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id"), nullable=False),
        sa.Column("competitor", sa.String(60), nullable=False),
        sa.Column("winner", sa.String(10), nullable=False),
        sa.Column("score_a", sa.Integer(), nullable=False),
        sa.Column("score_b", sa.Integer(), nullable=False),
        sa.Column("win_probability", sa.Float(), nullable=False),
        sa.Column("reasoning", sa.String(280), nullable=False),
        sa.Column("rendered_prompt", sa.Text(), nullable=False),
        sa.Column("commit_hash", sa.Text(), nullable=False),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revealed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("points_awarded", sa.Integer(), nullable=True),
        sa.UniqueConstraint("match_id", "competitor", name="uq_prediction_match_competitor"),
    )

    op.create_table(
        "content",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id"), nullable=False),
        sa.Column("template", sa.String(40), nullable=False),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("caption", sa.Text(), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "standings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("competitor", sa.String(60), nullable=False),
        sa.Column("scope", sa.String(20), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("accuracy", sa.Float(), nullable=False, server_default="0"),
        sa.Column("exact_scores", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("matches", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("competitor", "scope", name="uq_standing_competitor_scope"),
    )

    # DB-level lock enforcement (Postgres). On SQLite this is installed at
    # runtime by app.db_triggers.install_sqlite_trigger (demo/tests).
    if op.get_bind().dialect.name == "postgresql":
        op.execute(POSTGRES_UP)


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute(POSTGRES_DOWN)
    op.drop_table("standings")
    op.drop_table("content")
    op.drop_table("predictions")
    op.drop_table("consensus_odds")
    op.drop_table("odds")
    op.drop_table("matches")
    op.drop_table("teams")
