"""Auth services + route smoke tests (uses DATABASE_URL when present)."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.security import sha256_hex
from app.db.models import AuthIdentity, OAuthTransaction, User, UserSession
from app.db.session import get_engine
from app.main import app
from app.services.auth.google import GoogleIdentity
from app.services.auth.oauth_transactions import (
    consume_oauth_transaction,
    create_oauth_transaction,
)
from app.services.auth.sessions import (
    create_session,
    resolve_session_user,
    revoke_session,
)
from app.services.auth.users import upsert_user_from_google

load_dotenv()

pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL required for auth DB tests",
)


@pytest.fixture()
def db() -> Session:
    get_settings.cache_clear()
    import app.db.session as db_session

    db_session._engine = None
    db_session._SessionLocal = None
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def settings() -> Settings:
    get_settings.cache_clear()
    return get_settings()


def _cleanup_user(db: Session, email: str) -> None:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        return
    db.execute(delete(UserSession).where(UserSession.user_id == user.id))
    db.execute(delete(AuthIdentity).where(AuthIdentity.user_id == user.id))
    db.execute(delete(User).where(User.id == user.id))
    db.commit()


def test_upsert_google_user_and_session(db: Session, settings: Settings) -> None:
    email = "oauth-test@example.com"
    _cleanup_user(db, email)

    identity = GoogleIdentity(
        sub="google-sub-test-1",
        email=email,
        email_verified=True,
        name="OAuth Test",
        picture="https://example.com/a.png",
    )
    user = upsert_user_from_google(db, identity)
    row, raw = create_session(
        db,
        user=user,
        settings=settings,
        ip="127.0.0.1",
        user_agent="pytest",
    )
    db.commit()

    assert user.email == email
    assert row.token_hash == sha256_hex(raw)
    assert resolve_session_user(db, raw) is not None
    assert resolve_session_user(db, raw).id == user.id

    identity2 = GoogleIdentity(
        sub="google-sub-test-1",
        email=email,
        email_verified=True,
        name="OAuth Test 2",
        picture=None,
    )
    user2 = upsert_user_from_google(db, identity2)
    db.commit()
    assert user2.id == user.id
    assert user2.name == "OAuth Test 2"
    links = db.scalars(
        select(AuthIdentity).where(AuthIdentity.user_id == user.id)
    ).all()
    assert len(links) == 1

    assert revoke_session(db, raw) is True
    db.commit()
    assert resolve_session_user(db, raw) is None

    _cleanup_user(db, email)


def test_oauth_transaction_one_time(db: Session, settings: Settings) -> None:
    tx = create_oauth_transaction(db, settings)
    db.commit()
    consumed = consume_oauth_transaction(db, tx.state)
    db.commit()
    assert consumed.id == tx.id
    with pytest.raises(ValueError, match="already used"):
        consume_oauth_transaction(db, tx.state)

    db.execute(delete(OAuthTransaction).where(OAuthTransaction.id == tx.id))
    db.commit()


def test_oauth_transaction_expired(db: Session, settings: Settings) -> None:
    tx = create_oauth_transaction(db, settings)
    tx.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    with pytest.raises(ValueError, match="expired"):
        consume_oauth_transaction(db, tx.state)
    db.execute(delete(OAuthTransaction).where(OAuthTransaction.id == tx.id))
    db.commit()


def test_google_login_requires_config() -> None:
    from unittest.mock import MagicMock

    fake = MagicMock()
    fake.require_google_oauth.side_effect = RuntimeError(
        "Google OAuth is not configured"
    )
    app.dependency_overrides[get_settings] = lambda: fake
    try:
        client = TestClient(app)
        resp = client.get("/api/v1/auth/google/login", follow_redirects=False)
        assert resp.status_code == 503
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_me_unauthorized_without_cookie() -> None:
    client = TestClient(app)
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401
