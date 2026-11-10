"""add chat_sessions is_pinned + pinned_at

Revision ID: c4e8a1b2d903
Revises: 1921acd31921
Create Date: 2026-11-10
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4e8a1b2d903"
down_revision: Union[str, None] = "1921acd31921"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "chat_sessions",
        sa.Column(
            "is_pinned",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "chat_sessions",
        sa.Column("pinned_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "idx_chat_sessions_user_pinned",
        "chat_sessions",
        ["user_id", "is_pinned", "pinned_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_chat_sessions_user_pinned", table_name="chat_sessions")
    op.drop_column("chat_sessions", "pinned_at")
    op.drop_column("chat_sessions", "is_pinned")
