"""add chat_sessions run_status, active_run_id, last_read_at

Revision ID: d5f9b3c4e015
Revises: c4e8a1b2d903
Create Date: 2026-11-10
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d5f9b3c4e015"
down_revision: Union[str, None] = "c4e8a1b2d903"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "chat_sessions",
        sa.Column(
            "run_status",
            sa.Text(),
            nullable=False,
            server_default="idle",
        ),
    )
    op.add_column(
        "chat_sessions",
        sa.Column("active_run_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "chat_sessions",
        sa.Column("last_read_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("chat_sessions", "last_read_at")
    op.drop_column("chat_sessions", "active_run_id")
    op.drop_column("chat_sessions", "run_status")
