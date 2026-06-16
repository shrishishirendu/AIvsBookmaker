"""content: publishing lifecycle fields

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-16
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("content", sa.Column("publish_status", sa.String(12), nullable=False, server_default="draft"))
    op.add_column("content", sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("content", sa.Column("external_id", sa.String(120), nullable=True))
    op.add_column("content", sa.Column("publish_detail", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("content", "publish_detail")
    op.drop_column("content", "external_id")
    op.drop_column("content", "published_at")
    op.drop_column("content", "publish_status")
