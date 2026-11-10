"""Create / consume one-time OAuth login transactions."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import new_token, pkce_verifier
from app.db.models import OAuthTransaction


def create_oauth_transaction(db: Session, settings: Settings) -> OAuthTransaction:
    now = datetime.now(UTC)
    row = OAuthTransaction(
        state=new_token(24),
        code_verifier=pkce_verifier(),
        nonce=new_token(24),
        expires_at=now + timedelta(minutes=settings.oauth_transaction_ttl_minutes),
    )
    db.add(row)
    db.flush()
    return row


def consume_oauth_transaction(db: Session, state: str) -> OAuthTransaction:
    now = datetime.now(UTC)
    row = db.scalar(select(OAuthTransaction).where(OAuthTransaction.state == state))
    if row is None:
        raise ValueError("Unknown OAuth state")
    if row.consumed_at is not None:
        raise ValueError("OAuth state already used")
    if row.expires_at <= now:
        raise ValueError("OAuth state expired")

    row.consumed_at = now
    db.add(row)
    db.flush()
    return row


__all__ = ["create_oauth_transaction", "consume_oauth_transaction"]
