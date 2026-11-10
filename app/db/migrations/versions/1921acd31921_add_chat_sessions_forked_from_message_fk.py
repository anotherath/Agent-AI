"""add chat_sessions forked_from_message fk

Revision ID: 1921acd31921
Revises: 2a74f0b4cd22
Create Date: 2026-11-09
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "1921acd31921"
down_revision: Union[str, None] = "2a74f0b4cd22"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_foreign_key(
        "fk_chat_sessions_forked_from_message_id",
        "chat_sessions",
        "messages",
        ["forked_from_message_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_chat_sessions_forked_from_message_id",
        "chat_sessions",
        type_="foreignkey",
    )
