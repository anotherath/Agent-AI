"""add messages.parent_message_id

Revision ID: f7b1d8e9a234
Revises: e6a0c4d5f126
Create Date: 2026-11-10
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f7b1d8e9a234"
down_revision: Union[str, None] = "e6a0c4d5f126"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column("parent_message_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_messages_parent_message_id",
        "messages",
        "messages",
        ["parent_message_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "idx_messages_parent_message_id",
        "messages",
        ["parent_message_id"],
    )
    # Linear backfill: each message parents the previous in the same session.
    # FE still collapses legacy regenerate duplicates (same consecutive user text).
    op.execute(
        """
        WITH ordered AS (
            SELECT
                id,
                session_id,
                LAG(id) OVER (
                    PARTITION BY session_id
                    ORDER BY created_at ASC, id ASC
                ) AS prev_id
            FROM messages
        )
        UPDATE messages AS m
        SET parent_message_id = ordered.prev_id
        FROM ordered
        WHERE m.id = ordered.id
          AND ordered.prev_id IS NOT NULL
          AND m.parent_message_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index("idx_messages_parent_message_id", table_name="messages")
    op.drop_constraint(
        "fk_messages_parent_message_id",
        "messages",
        type_="foreignkey",
    )
    op.drop_column("messages", "parent_message_id")
