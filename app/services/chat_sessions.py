"""Chat session / subsession rules and context assembly."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import ChatSession, Message, Project
from app.services.errors import ConflictError, ForbiddenError, NotFoundError, ServiceError

MAX_PINNED_SESSIONS = 3
MIN_SEARCH_QUERY_LEN = 2
SEARCH_SCAN_CAP = 200
SearchScope = Literal["all", "title", "messages"]


@dataclass(frozen=True)
class SessionSearchHit:
    session: ChatSession
    match_in: Literal["title", "message"]
    snippet: str
    message_id: uuid.UUID | None


def get_owned_session(
    db: Session,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> ChatSession:
    row = db.scalar(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id,
        )
    )
    if row is None:
        raise NotFoundError("Chat session not found")
    return row


DEFAULT_SESSION_PAGE_LIMIT = 20
MAX_SESSION_PAGE_LIMIT = 100


def _main_sessions_filters(
    user_id: uuid.UUID,
    *,
    project_id: uuid.UUID | None = None,
):
    filters = [
        ChatSession.user_id == user_id,
        ChatSession.is_main.is_(True),
    ]
    if project_id is not None:
        filters.append(ChatSession.project_id == project_id)
    return filters


def list_main_sessions(
    db: Session,
    user_id: uuid.UUID,
    *,
    project_id: uuid.UUID | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[ChatSession]:
    """List main sessions. `limit=None` → lấy hết (nội bộ/test)."""
    stmt = select(ChatSession).where(
        *_main_sessions_filters(user_id, project_id=project_id)
    )
    # Pinned trước (pinned_at mới nhất); còn lại theo last_message_at
    # (fallback updated_at cho session chưa có message).
    stmt = stmt.order_by(
        ChatSession.is_pinned.desc(),
        ChatSession.pinned_at.desc().nulls_last(),
        func.coalesce(
            ChatSession.last_message_at,
            ChatSession.updated_at,
        ).desc(),
    )
    if offset:
        stmt = stmt.offset(max(0, offset))
    if limit is not None:
        stmt = stmt.limit(max(0, limit))
    return list(db.scalars(stmt).all())


def count_main_sessions(
    db: Session,
    user_id: uuid.UUID,
    *,
    project_id: uuid.UUID | None = None,
) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(ChatSession)
            .where(*_main_sessions_filters(user_id, project_id=project_id))
        )
        or 0
    )


def list_main_sessions_page(
    db: Session,
    user_id: uuid.UUID,
    *,
    project_id: uuid.UUID | None = None,
    limit: int = DEFAULT_SESSION_PAGE_LIMIT,
    offset: int = 0,
) -> tuple[list[ChatSession], bool]:
    """Return `(rows, has_more)` using limit+1 — no COUNT(*) round-trip."""
    limit = min(max(1, limit), MAX_SESSION_PAGE_LIMIT)
    offset = max(0, offset)
    rows = list_main_sessions(
        db,
        user_id,
        project_id=project_id,
        limit=limit + 1,
        offset=offset,
    )
    has_more = len(rows) > limit
    return rows[:limit], has_more


def _count_pinned_sessions(db: Session, user_id: uuid.UUID) -> int:
    """Đếm pin của user (main + sub) — chung 1 hạn mức."""
    return int(
        db.scalar(
            select(func.count())
            .select_from(ChatSession)
            .where(
                ChatSession.user_id == user_id,
                ChatSession.is_pinned.is_(True),
            )
        )
        or 0
    )


def pin_session(
    db: Session,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> ChatSession:
    """Pin main hoặc sub. Mỗi user tối đa MAX_PINNED_SESSIONS (chung)."""
    row = get_owned_session(db, user_id, session_id)
    if row.is_pinned:
        return row

    if _count_pinned_sessions(db, user_id) >= MAX_PINNED_SESSIONS:
        raise ConflictError(
            f"Pin limit reached (max {MAX_PINNED_SESSIONS} sessions)"
        )

    now = datetime.now(UTC)
    row.is_pinned = True
    row.pinned_at = now
    row.updated_at = now
    db.add(row)
    db.flush()
    return row


def unpin_session(
    db: Session,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> ChatSession:
    row = get_owned_session(db, user_id, session_id)
    if not row.is_pinned:
        return row

    row.is_pinned = False
    row.pinned_at = None
    row.updated_at = datetime.now(UTC)
    db.add(row)
    db.flush()
    return row


def create_main_session(
    db: Session,
    user_id: uuid.UUID,
    *,
    title: str | None = None,
    project_id: uuid.UUID | None = None,
) -> ChatSession:
    if project_id is not None:
        project = db.scalar(
            select(Project).where(Project.id == project_id, Project.user_id == user_id)
        )
        if project is None:
            raise NotFoundError("Project not found")

    now = datetime.now(UTC)
    row = ChatSession(
        user_id=user_id,
        project_id=project_id,
        title=title,
        is_main=True,
        parent_session_id=None,
        forked_from_message_id=None,
        run_status="idle",
        last_read_at=now,
    )
    db.add(row)
    db.flush()
    return row


def update_session_title(
    db: Session,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    *,
    title: str | None,
) -> ChatSession:
    row = get_owned_session(db, user_id, session_id)
    row.title = title
    row.updated_at = datetime.now(UTC)
    db.add(row)
    db.flush()
    return row


def delete_session(db: Session, user_id: uuid.UUID, session_id: uuid.UUID) -> None:
    row = get_owned_session(db, user_id, session_id)
    db.delete(row)
    db.flush()


def list_subsessions(
    db: Session,
    user_id: uuid.UUID,
    parent_id: uuid.UUID,
) -> list[ChatSession]:
    parent = get_owned_session(db, user_id, parent_id)
    if not parent.is_main:
        raise ServiceError("Only main sessions have subsessions")
    return list(
        db.scalars(
            select(ChatSession)
            .where(ChatSession.parent_session_id == parent.id)
            .order_by(
                ChatSession.is_pinned.desc(),
                ChatSession.pinned_at.desc().nulls_last(),
                ChatSession.created_at.asc(),
            )
        ).all()
    )


def fork_subsession(
    db: Session,
    user_id: uuid.UUID,
    parent_id: uuid.UUID,
    *,
    forked_from_message_id: uuid.UUID,
) -> ChatSession:
    """Tạo sub với title=null; tin đầu trên sub sẽ auto-title như main."""
    parent = get_owned_session(db, user_id, parent_id)
    if not parent.is_main:
        raise ForbiddenError("Cannot fork from a subsession")

    message = db.scalar(
        select(Message).where(
            Message.id == forked_from_message_id,
            Message.session_id == parent.id,
        )
    )
    if message is None:
        raise NotFoundError("Fork message not found on main session")

    now = datetime.now(UTC)
    row = ChatSession(
        user_id=user_id,
        project_id=parent.project_id,
        title=None,
        is_main=False,
        parent_session_id=parent.id,
        forked_from_message_id=message.id,
        run_status="idle",
        last_read_at=now,
    )
    db.add(row)
    parent.updated_at = now
    db.add(parent)
    db.flush()
    return row


def list_session_messages(
    db: Session,
    session: ChatSession,
) -> list[Message]:
    return list(
        db.scalars(
            select(Message)
            .where(Message.session_id == session.id)
            .order_by(Message.created_at.asc())
        ).all()
    )


def assemble_context_messages(
    db: Session,
    session: ChatSession,
) -> list[Message]:
    """History for agent: main prefix through fork point + sub messages."""
    if session.is_main:
        return list_session_messages(db, session)

    if session.parent_session_id is None or session.forked_from_message_id is None:
        raise ServiceError("Invalid subsession")

    fork_msg = db.get(Message, session.forked_from_message_id)
    if fork_msg is None:
        raise NotFoundError("Fork point message missing")

    parent_msgs = list(
        db.scalars(
            select(Message)
            .where(Message.session_id == session.parent_session_id)
            .order_by(Message.created_at.asc(), Message.id.asc())
        ).all()
    )
    prefix: list[Message] = []
    for msg in parent_msgs:
        prefix.append(msg)
        if msg.id == fork_msg.id:
            break
    else:
        raise NotFoundError("Fork point message missing on parent session")

    branch = list_session_messages(db, session)
    return prefix + branch


def touch_session(db: Session, session: ChatSession) -> None:
    """Bump updated_at + last_message_at (và parent main nếu đây là sub)."""
    now = datetime.now(UTC)
    session.updated_at = now
    session.last_message_at = now
    db.add(session)
    if not session.is_main and session.parent_session_id is not None:
        parent = db.get(ChatSession, session.parent_session_id)
        if parent is not None:
            parent.updated_at = now
            parent.last_message_at = now
            db.add(parent)


def mark_session_read(
    db: Session,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> ChatSession:
    """Đánh dấu đã đọc — không đụng updated_at (tránh nhảy sort list)."""
    row = get_owned_session(db, user_id, session_id)
    row.last_read_at = datetime.now(UTC)
    db.add(row)
    db.flush()
    return row


def map_has_unread(
    sessions: list[ChatSession],
) -> dict[uuid.UUID, bool]:
    """has_unread = last_message_at mới hơn last_read_at (không scan messages)."""
    out: dict[uuid.UUID, bool] = {}
    for session in sessions:
        ts = session.last_message_at
        if ts is None:
            out[session.id] = False
        elif session.last_read_at is None:
            out[session.id] = True
        else:
            out[session.id] = ts > session.last_read_at
    return out


def session_has_unread(_db: Session, session: ChatSession) -> bool:
    return map_has_unread([session]).get(session.id, False)


def _escape_ilike(raw: str) -> str:
    """Escape %, _, \\ for ILIKE with escape='\\'."""
    return (
        raw.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


def _snippet(content: str, query: str, *, radius: int = 60) -> str:
    text = content or ""
    q = (query or "").strip()
    if not text:
        return ""
    if not q:
        cut = text[: max(radius * 2, 120)]
        return cut + ("…" if len(text) > len(cut) else "")
    lower = text.lower()
    idx = lower.find(q.lower())
    if idx < 0:
        cut = text[: max(radius * 2, 120)]
        return cut + ("…" if len(text) > len(cut) else "")
    start = max(0, idx - radius)
    end = min(len(text), idx + len(q) + radius)
    out = text[start:end]
    if start > 0:
        out = "…" + out
    if end < len(text):
        out = out + "…"
    return out


def _session_activity_ts(session: ChatSession) -> datetime:
    return session.last_message_at or session.updated_at


def search_sessions(
    db: Session,
    user_id: uuid.UUID,
    *,
    q: str,
    scope: SearchScope = "all",
    project_id: uuid.UUID | None = None,
    limit: int = DEFAULT_SESSION_PAGE_LIMIT,
    offset: int = 0,
) -> tuple[list[SessionSearchHit], bool]:
    """Tìm session theo title và/hoặc nội dung message (ILIKE).

    Dedup theo session_id: ưu tiên match title; không thì 1 message hit mới nhất.
    Trả `(hits, has_more)` với limit+1.
    """
    query = (q or "").strip()
    if len(query) < MIN_SEARCH_QUERY_LEN:
        raise ServiceError(
            f"q must be at least {MIN_SEARCH_QUERY_LEN} characters",
            status_code=400,
        )
    if scope not in {"all", "title", "messages"}:
        raise ServiceError("scope must be all, title, or messages", status_code=400)

    limit = min(max(1, limit), MAX_SESSION_PAGE_LIMIT)
    offset = max(0, offset)
    pattern = f"%{_escape_ilike(query)}%"

    session_filters = [ChatSession.user_id == user_id]
    if project_id is not None:
        session_filters.append(ChatSession.project_id == project_id)

    hits: dict[uuid.UUID, SessionSearchHit] = {}

    if scope in {"all", "title"}:
        title_rows = list(
            db.scalars(
                select(ChatSession)
                .where(
                    *session_filters,
                    ChatSession.title.is_not(None),
                    ChatSession.title.ilike(pattern, escape="\\"),
                )
                .order_by(
                    ChatSession.is_pinned.desc(),
                    func.coalesce(
                        ChatSession.last_message_at,
                        ChatSession.updated_at,
                    ).desc(),
                )
                .limit(SEARCH_SCAN_CAP)
            ).all()
        )
        for row in title_rows:
            hits[row.id] = SessionSearchHit(
                session=row,
                match_in="title",
                snippet=(row.title or "").strip(),
                message_id=None,
            )

    if scope in {"all", "messages"}:
        msg_rows = list(
            db.execute(
                select(Message, ChatSession)
                .join(ChatSession, Message.session_id == ChatSession.id)
                .where(
                    *session_filters,
                    Message.content.ilike(pattern, escape="\\"),
                )
                .order_by(Message.created_at.desc())
                .limit(SEARCH_SCAN_CAP)
            ).all()
        )
        for msg, session in msg_rows:
            if session.id in hits:
                continue
            hits[session.id] = SessionSearchHit(
                session=session,
                match_in="message",
                snippet=_snippet(msg.content, query),
                message_id=msg.id,
            )

    ordered = sorted(
        hits.values(),
        key=lambda h: (
            0 if h.session.is_pinned else 1,
            -_session_activity_ts(h.session).timestamp(),
        ),
    )
    window = ordered[offset : offset + limit + 1]
    has_more = len(window) > limit
    return window[:limit], has_more
