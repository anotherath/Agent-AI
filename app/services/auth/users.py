"""Upsert app user from verified Google identity."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AuthIdentity, User
from app.services.auth.google import GoogleIdentity

GOOGLE_PROVIDER = "google"


def upsert_user_from_google(db: Session, identity: GoogleIdentity) -> User:
    now = datetime.now(UTC)

    existing_link = db.scalar(
        select(AuthIdentity).where(
            AuthIdentity.provider == GOOGLE_PROVIDER,
            AuthIdentity.provider_user_id == identity.sub,
        )
    )
    if existing_link is not None:
        user = db.get(User, existing_link.user_id)
        if user is None:
            raise RuntimeError("auth_identity references missing user")
        _apply_profile(user, identity, now)
        user.last_login_at = now
        db.add(user)
        db.flush()
        return user

    user = db.scalar(select(User).where(User.email == identity.email))
    if user is None:
        user = User(
            email=identity.email,
            email_verified=identity.email_verified,
            name=identity.name,
            avatar_url=identity.picture,
            status="active",
            last_login_at=now,
        )
        db.add(user)
        db.flush()
    else:
        _apply_profile(user, identity, now)
        user.last_login_at = now
        db.add(user)
        db.flush()

    db.add(
        AuthIdentity(
            user_id=user.id,
            provider=GOOGLE_PROVIDER,
            provider_user_id=identity.sub,
        )
    )
    db.flush()
    return user


def _apply_profile(user: User, identity: GoogleIdentity, now: datetime) -> None:
    user.email = identity.email
    user.email_verified = identity.email_verified
    if identity.name:
        user.name = identity.name
    if identity.picture:
        user.avatar_url = identity.picture
    user.updated_at = now


__all__ = ["GOOGLE_PROVIDER", "upsert_user_from_google"]
