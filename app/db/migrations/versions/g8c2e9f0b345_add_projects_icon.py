"""add projects.icon

Revision ID: g8c2e9f0b345
Revises: f7b1d8e9a234
Create Date: 2026-11-10
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "g8c2e9f0b345"
down_revision: Union[str, None] = "f7b1d8e9a234"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column(
            "icon",
            sa.Text(),
            nullable=False,
            server_default="folder",
        ),
    )


def downgrade() -> None:
    op.drop_column("projects", "icon")
