"""Message persistence helpers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ChatSession, Message
from app.services.chat_sessions import fork_subsession, get_owned_session, touch_session
from app.services.errors import NotFoundError, ServiceError


def add_message(
    db: Session,
    session: ChatSession,
    *,
    role: str,
    content: str,
    metadata: dict[str, Any] | None = None,
    parent_message_id: uuid.UUID | None = None,
) -> Message:
    msg = Message(
        session_id=session.id,
        role=role,
        content=content,
        metadata_=metadata,
        parent_message_id=parent_message_id,
        created_at=datetime.now(UTC),
    )
    db.add(msg)
    touch_session(db, session)
    db.flush()
    return msg


def get_session_message(
    db: Session,
    session: ChatSession,
    message_id: uuid.UUID,
) -> Message:
    msg = db.scalar(
        select(Message).where(
            Message.id == message_id,
            Message.session_id == session.id,
        )
    )
    if msg is None:
        raise NotFoundError("Message not found")
    return msg


def latest_message(db: Session, session: ChatSession) -> Message | None:
    return db.scalar(
        select(Message)
        .where(Message.session_id == session.id)
        .order_by(Message.created_at.desc())
        .limit(1)
    )


def prepare_edit_target(
    db: Session,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    message_id: uuid.UUID,
    *,
    new_content: str,
) -> tuple[ChatSession, Message]:
    """Edit on main: latest → same session; older → fork subsession then user msg."""
    session = get_owned_session(db, user_id, session_id)
    if not session.is_main:
        raise ServiceError("Edit-with-fork rules apply to main session only")

    target = get_session_message(db, session, message_id)
    if target.role != "user":
        raise ServiceError("Only user messages can be edited this way")

    latest = latest_message(db, session)
    if latest is not None and latest.id == target.id:
        # Replace content on latest user message and continue on main
        target.content = new_content
        db.add(target)
        touch_session(db, session)
        db.flush()
        return session, target

    sub = fork_subsession(
        db,
        user_id,
        session.id,
        forked_from_message_id=target.id,
    )
    user_msg = add_message(
        db,
        sub,
        role="user",
        content=new_content,
        parent_message_id=None,
    )
    return sub, user_msg


def prepare_regenerate_target(
    db: Session,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    *,
    user_message_id: uuid.UUID | None = None,
) -> tuple[ChatSession, Message]:
    """Reuse an existing user message for regenerate (no new user row)."""
    session = get_owned_session(db, user_id, session_id)

    if user_message_id is not None:
        user_msg = get_session_message(db, session, user_message_id)
        if user_msg.role != "user":
            raise ServiceError("Regenerate target must be a user message")
        return session, user_msg

    # Prefer the latest user message (parent of the assistant being regenerated).
    rows = list(
        db.scalars(
            select(Message)
            .where(
                Message.session_id == session.id,
                Message.role == "user",
            )
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(1)
        ).all()
    )
    if not rows:
        raise ServiceError("No user message to regenerate from")
    return session, rows[0]


def prepare_ask_from_selection(
    db: Session,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    *,
    message_id: uuid.UUID,
    selected_text: str,
    target: str,
    question: str,
) -> tuple[ChatSession, Message]:
    session = get_owned_session(db, user_id, session_id)
    content = (
        f"Regarding this excerpt:\n\"\"\"\n{selected_text.strip()}\n\"\"\"\n\n"
        f"{question.strip()}"
    )

    if target == "main":
        if not session.is_main:
            # Asking on main while currently in sub: post to parent main
            if session.parent_session_id is None:
                raise ServiceError("Invalid session")
            main = get_owned_session(db, user_id, session.parent_session_id)
            latest = latest_message(db, main)
            user_msg = add_message(
                db,
                main,
                role="user",
                content=content,
                parent_message_id=latest.id if latest else None,
            )
            return main, user_msg
        latest = latest_message(db, session)
        user_msg = add_message(
            db,
            session,
            role="user",
            content=content,
            parent_message_id=latest.id if latest else None,
        )
        return session, user_msg

    if target != "subsession":
        raise ServiceError("target must be 'main' or 'subsession'")

    if session.is_main:
        get_session_message(db, session, message_id)  # ensure message on main
        sub = fork_subsession(
            db,
            user_id,
            session.id,
            forked_from_message_id=message_id,
        )
        user_msg = add_message(db, sub, role="user", content=content)
        return sub, user_msg

    # Already in a subsession: continue on this branch
    latest = latest_message(db, session)
    user_msg = add_message(
        db,
        session,
        role="user",
        content=content,
        parent_message_id=latest.id if latest else None,
    )
    return session, user_msg


def messages_to_agent_history(messages: list[Message]) -> list[dict[str, str]]:
    from app.services.selection_directives import expand_selection_directives

    out: list[dict[str, str]] = []
    for msg in messages:
        if msg.role in {"user", "assistant", "system"}:
            content = msg.content
            if msg.role == "user":
                content = expand_selection_directives(content)
            out.append({"role": msg.role, "content": content})
    return out
