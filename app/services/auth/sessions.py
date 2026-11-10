"""Server-side long-lived sessions (cookie holds opaque token)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import Settings
from app.core.security import new_token, sha256_hex
from app.db.models import User, UserSession


def create_session(
    db: Session,
    *,
    user: User,
    settings: Settings,
    ip: str | None,
    user_agent: str | None,
) -> tuple[UserSession, str]:
    raw_token = new_token(32)
    now = datetime.now(UTC)
    row = UserSession(
        user_id=user.id,
        token_hash=sha256_hex(raw_token),
        expires_at=now + timedelta(days=settings.session_ttl_days),
        ip=ip,
        user_agent=user_agent,
    )
    db.add(row)
    db.flush()
    return row, raw_token


def resolve_session_user(db: Session, raw_token: str | None) -> User | None:
    if not raw_token:
        return None

    row = db.scalar(
        select(UserSession)
        .options(joinedload(UserSession.user))
        .where(UserSession.token_hash == sha256_hex(raw_token))
    )
    if row is None:
        return None

    now = datetime.now(UTC)
    if row.revoked_at is not None:
        return None
    if row.expires_at <= now:
        return None
    if row.user.status != "active":
        return None
    return row.user


def revoke_session(db: Session, raw_token: str | None) -> bool:
    if not raw_token:
        return False

    row = db.scalar(
        select(UserSession).where(UserSession.token_hash == sha256_hex(raw_token))
    )
    if row is None:
        return False
    if row.revoked_at is None:
        row.revoked_at = datetime.now(UTC)
        db.add(row)
        db.flush()
    return True


__all__ = ["create_session", "resolve_session_user", "revoke_session"]
