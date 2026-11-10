"""add chat_sessions.last_message_at

Revision ID: e6a0c4d5f126
Revises: d5f9b3c4e015
Create Date: 2026-11-10
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e6a0c4d5f126"
down_revision: Union[str, None] = "d5f9b3c4e015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "chat_sessions",
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Backfill theo message của chính session.
    op.execute(
        """
        UPDATE chat_sessions AS cs
        SET last_message_at = src.mx
        FROM (
            SELECT session_id, MAX(created_at) AS mx
            FROM messages
            GROUP BY session_id
        ) AS src
        WHERE cs.id = src.session_id
        """
    )
    # Main: lấy max(own, max(subs)) để list phản ánh cả nhánh.
    op.execute(
        """
        UPDATE chat_sessions AS main
        SET last_message_at = src.mx
        FROM (
            SELECT
                main.id AS id,
                GREATEST(
                    COALESCE(main.last_message_at, TIMESTAMPTZ '-infinity'),
                    COALESCE(MAX(sub.last_message_at), TIMESTAMPTZ '-infinity')
                ) AS mx
            FROM chat_sessions AS main
            LEFT JOIN chat_sessions AS sub
                ON sub.parent_session_id = main.id
            WHERE main.is_main = true
            GROUP BY main.id, main.last_message_at
        ) AS src
        WHERE main.id = src.id
          AND src.mx > TIMESTAMPTZ '-infinity'
        """
    )


def downgrade() -> None:
    op.drop_column("chat_sessions", "last_message_at")
