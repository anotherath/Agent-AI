"""SQLAlchemy engine + session cho Supabase Postgres."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is not None:
        return _engine

    url = get_settings().database_url
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Add it to .env "
            "(Supabase → Database → Transaction pooler)."
        )

    _engine = create_engine(
        url,
        pool_pre_ping=True,
    )
    _SessionLocal = sessionmaker(
        bind=_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    return _engine


def SessionLocal() -> Session:
    """Tạo session mới (background task / ngoài request scope)."""
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


__all__ = ["get_engine", "get_db", "SessionLocal"]
