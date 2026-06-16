"""Core data model (BUILD_SPEC §10).

The predictions table is where the moat lives: commit_hash + committed_at are
written at COMMIT, locked_at at LOCK, revealed flipped at REVEAL. A DB-level
trigger (see app/db_triggers.py) refuses to mutate the prediction payload once
locked_at is set — the lock is enforced in the database, not just app code.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    fifa_rank: Mapped[int] = mapped_column(Integer)
    elo: Mapped[int] = mapped_column(Integer)
    gf: Mapped[int] = mapped_column(Integer, default=0)
    ga: Mapped[int] = mapped_column(Integer, default=0)
    last5: Mapped[str] = mapped_column(String(10), default="")


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(primary_key=True)  # = API-Football fixture id
    team_a: Mapped[str] = mapped_column(String(80))
    team_b: Mapped[str] = mapped_column(String(80))
    team_a_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    team_b_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    stage: Mapped[str] = mapped_column(String(40))
    kickoff_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    venue: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="NS")
    degraded: Mapped[bool] = mapped_column(Boolean, default=False)

    locked: Mapped[bool] = mapped_column(Boolean, default=False)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    final_score_a: Mapped[int | None] = mapped_column(Integer, nullable=True)
    final_score_b: Mapped[int | None] = mapped_column(Integer, nullable=True)

    predictions: Mapped[list["Prediction"]] = relationship(
        back_populates="match", cascade="all, delete-orphan"
    )


class Odds(Base):
    __tablename__ = "odds"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"))
    book: Mapped[str] = mapped_column(String(40))
    home: Mapped[float] = mapped_column(Float)
    draw: Mapped[float] = mapped_column(Float)
    away: Mapped[float] = mapped_column(Float)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ConsensusOdds(Base):
    __tablename__ = "consensus_odds"

    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), primary_key=True)
    home_pct: Mapped[float] = mapped_column(Float)
    draw_pct: Mapped[float] = mapped_column(Float)
    away_pct: Mapped[float] = mapped_column(Float)
    overround: Mapped[float] = mapped_column(Float)


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        # one prediction per competitor per match
        UniqueConstraint("match_id", "competitor", name="uq_prediction_match_competitor"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"))
    competitor: Mapped[str] = mapped_column(String(60))  # model | bookmaker | user:{id}

    winner: Mapped[str] = mapped_column(String(10))
    score_a: Mapped[int] = mapped_column(Integer)
    score_b: Mapped[int] = mapped_column(Integer)
    win_probability: Mapped[float] = mapped_column(Float)
    reasoning: Mapped[str] = mapped_column(String(280))
    rendered_prompt: Mapped[str] = mapped_column(Text)

    commit_hash: Mapped[str] = mapped_column(Text)
    committed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revealed: Mapped[bool] = mapped_column(Boolean, default=False)
    points_awarded: Mapped[int | None] = mapped_column(Integer, nullable=True)

    match: Mapped["Match"] = relationship(back_populates="predictions")


class Content(Base):
    __tablename__ = "content"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"))
    template: Mapped[str] = mapped_column(String(40))
    platform: Mapped[str] = mapped_column(String(20))
    caption: Mapped[str] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    # image_spec / facts used to render the card; lets admin re-render without recompute
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # whether this template's auto-trigger condition fired (Contrarian/Bookmaker)
    triggered: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # publishing lifecycle: draft -> queued -> posted | skipped | failed
    publish_status: Mapped[str] = mapped_column(String(12), default="draft")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    publish_detail: Mapped[str | None] = mapped_column(Text, nullable=True)


class Standing(Base):
    __tablename__ = "standings"
    __table_args__ = (
        UniqueConstraint("competitor", "scope", name="uq_standing_competitor_scope"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    competitor: Mapped[str] = mapped_column(String(60))
    scope: Mapped[str] = mapped_column(String(20))  # overall | weekly | knockout
    points: Mapped[int] = mapped_column(Integer, default=0)
    accuracy: Mapped[float] = mapped_column(Float, default=0.0)
    exact_scores: Mapped[int] = mapped_column(Integer, default=0)
    matches: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
