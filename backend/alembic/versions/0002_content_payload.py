"""content: add payload + triggered

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-16
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("content", sa.Column("payload", sa.JSON(), nullable=True))
    op.add_column(
        "content",
        sa.Column("triggered", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("content", "triggered")
    op.drop_column("content", "payload")
