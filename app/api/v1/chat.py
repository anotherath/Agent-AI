"""Chat sessions + messages (+ SSE agent)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.errors import raise_service_error
from app.api.sse import stream_run_sse
from app.db.models import ChatSession, User
from app.db.session import get_db
from app.schemas.chat import (
    AskFromSelectionRequest,
    ChatMessageCreate,
    ChatSessionCreate,
    ChatSessionListOut,
    ChatSessionOut,
    ChatSessionUpdate,
    ForkRequest,
    MessageEditRequest,
    MessageOut,
    MessageRegenerateRequest,
)
from app.services import chat_runs
from app.services import chat_sessions as chat_svc
from app.services import messages as messages_svc
from app.services.chat_sessions import (
    DEFAULT_SESSION_PAGE_LIMIT,
    MAX_SESSION_PAGE_LIMIT,
)
from app.services.errors import ServiceError

router = APIRouter(prefix="/chat", tags=["chat"])

_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


def _message_out(msg) -> MessageOut:
    return MessageOut(
        id=msg.id,
        session_id=msg.session_id,
        parent_message_id=msg.parent_message_id,
        role=msg.role,
        content=msg.content,
        metadata=msg.metadata_,
        created_at=msg.created_at,
    )


def _session_out(
    db: Session,
    row: ChatSession,
    *,
    has_unread: bool | None = None,
) -> ChatSessionOut:
    unread = (
        has_unread
        if has_unread is not None
        else chat_svc.session_has_unread(db, row)
    )
    return ChatSessionOut(
        id=row.id,
        project_id=row.project_id,
        title=row.title,
        is_main=row.is_main,
        is_pinned=row.is_pinned,
        pinned_at=row.pinned_at,
        run_status=row.run_status,  # type: ignore[arg-type]
        active_run_id=row.active_run_id,
        last_read_at=row.last_read_at,
        last_message_at=row.last_message_at,
        has_unread=unread,
        parent_session_id=row.parent_session_id,
        forked_from_message_id=row.forked_from_message_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _sessions_out(db: Session, rows: list[ChatSession]) -> list[ChatSessionOut]:
    # Only running rows can be stale — skip heal work for idle/completed.
    healed: list[ChatSession] = []
    for row in rows:
        if row.run_status == "running":
            healed.append(chat_runs.heal_stale_run_state(db, row))
        else:
            healed.append(row)
    unread_map = chat_svc.map_has_unread(healed)
    return [
        _session_out(db, row, has_unread=unread_map.get(row.id, False))
        for row in healed
    ]


async def _start_and_stream(
    *,
    user: User,
    session: ChatSession,
    user_msg,
) -> StreamingResponse:
    try:
        run_id = await chat_runs.start_chat_run(
            user_id=user.id,
            session_id=session.id,
            user_message_id=user_msg.id,
        )
    except ServiceError as exc:
        raise_service_error(exc)
    return StreamingResponse(
        stream_run_sse(run_id),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


@router.get("/sessions", response_model=ChatSessionListOut)
def list_sessions(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    project_id: uuid.UUID | None = None,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=MAX_SESSION_PAGE_LIMIT,
            description="Số session mỗi trang",
        ),
    ] = DEFAULT_SESSION_PAGE_LIMIT,
    offset: Annotated[
        int,
        Query(ge=0, description="Bỏ qua N session đầu (sau sort)"),
    ] = 0,
) -> ChatSessionListOut:
    rows, has_more = chat_svc.list_main_sessions_page(
        db,
        user.id,
        project_id=project_id,
        limit=limit,
        offset=offset,
    )
    # Estimate only — avoid COUNT(*) on every page fetch.
    total = offset + len(rows) + (1 if has_more else 0)
    return ChatSessionListOut(
        items=_sessions_out(db, rows),
        total=total,
        limit=limit,
        offset=offset,
        has_more=has_more,
    )


@router.post("/sessions", response_model=ChatSessionOut, status_code=201)
def create_session(
    body: ChatSessionCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ChatSessionOut:
    try:
        row = chat_svc.create_main_session(
            db,
            user.id,
            title=body.title,
            project_id=body.project_id,
        )
        db.commit()
        db.refresh(row)
    except ServiceError as exc:
        raise_service_error(exc)
    return _session_out(db, row)


@router.get("/sessions/{session_id}", response_model=ChatSessionOut)
def get_session(
    session_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ChatSessionOut:
    try:
        row = chat_svc.get_owned_session(db, user.id, session_id)
        row = chat_runs.heal_stale_run_state(db, row)
    except ServiceError as exc:
        raise_service_error(exc)
    return _session_out(db, row)


@router.post("/sessions/{session_id}/read", response_model=ChatSessionOut)
def mark_session_read(
    session_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ChatSessionOut:
    try:
        row = chat_svc.mark_session_read(db, user.id, session_id)
        db.commit()
        db.refresh(row)
    except ServiceError as exc:
        raise_service_error(exc)
    return _session_out(db, row, has_unread=False)


@router.patch("/sessions/{session_id}", response_model=ChatSessionOut)
def patch_session(
    session_id: uuid.UUID,
    body: ChatSessionUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ChatSessionOut:
    try:
        row = chat_svc.update_session_title(
            db, user.id, session_id, title=body.title
        )
        db.commit()
        db.refresh(row)
    except ServiceError as exc:
        raise_service_error(exc)
    return _session_out(db, row)


@router.post("/sessions/{session_id}/pin", response_model=ChatSessionOut)
def pin_session(
    session_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ChatSessionOut:
    try:
        row = chat_svc.pin_session(db, user.id, session_id)
        db.commit()
        db.refresh(row)
    except ServiceError as exc:
        raise_service_error(exc)
    return _session_out(db, row)


@router.delete("/sessions/{session_id}/pin", response_model=ChatSessionOut)
def unpin_session(
    session_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ChatSessionOut:
    try:
        row = chat_svc.unpin_session(db, user.id, session_id)
        db.commit()
        db.refresh(row)
    except ServiceError as exc:
        raise_service_error(exc)
    return _session_out(db, row)


@router.delete("/sessions/{session_id}", status_code=204, response_class=Response)
def delete_session(
    session_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    try:
        chat_svc.delete_session(db, user.id, session_id)
        db.commit()
    except ServiceError as exc:
        raise_service_error(exc)
    return Response(status_code=204)


@router.get(
    "/sessions/{session_id}/subsessions",
    response_model=list[ChatSessionOut],
)
def list_subsessions(
    session_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ChatSessionOut]:
    try:
        rows = chat_svc.list_subsessions(db, user.id, session_id)
    except ServiceError as exc:
        raise_service_error(exc)
    return _sessions_out(db, rows)


@router.post(
    "/sessions/{session_id}/fork",
    response_model=ChatSessionOut,
    status_code=201,
)
def fork_session(
    session_id: uuid.UUID,
    body: ForkRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ChatSessionOut:
    try:
        row = chat_svc.fork_subsession(
            db,
            user.id,
            session_id,
            forked_from_message_id=body.forked_from_message_id,
            title=body.title,
        )
        db.commit()
        db.refresh(row)
    except ServiceError as exc:
        raise_service_error(exc)
    return _session_out(db, row)


@router.get(
    "/sessions/{session_id}/messages",
    response_model=list[MessageOut],
)
def list_messages(
    session_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[MessageOut]:
    try:
        session = chat_svc.get_owned_session(db, user.id, session_id)
        rows = chat_svc.list_session_messages(db, session)
    except ServiceError as exc:
        raise_service_error(exc)
    return [_message_out(m) for m in rows]


@router.get(
    "/sessions/{session_id}/context",
    response_model=list[MessageOut],
)
def get_context(
    session_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[MessageOut]:
    try:
        session = chat_svc.get_owned_session(db, user.id, session_id)
        rows = chat_svc.assemble_context_messages(db, session)
    except ServiceError as exc:
        raise_service_error(exc)
    return [_message_out(m) for m in rows]


@router.get("/sessions/{session_id}/runs/{run_id}/stream")
async def stream_existing_run(
    session_id: uuid.UUID,
    run_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> StreamingResponse:
    """Reconnect SSE tới run đang chạy / vừa xong (replay + live)."""
    try:
        session = chat_svc.get_owned_session(db, user.id, session_id)
        session = chat_runs.heal_stale_run_state(db, session)
    except ServiceError as exc:
        raise_service_error(exc)

    run = chat_runs.get_run(run_id)
    if run is None or run.session_id != session.id or run.user_id != user.id:
        # Heal leftover DB "running" when process no longer has the run.
        if (
            session.active_run_id == run_id
            and session.run_status == "running"
            and not chat_runs.get_run(run_id)
        ):
            chat_runs.heal_stale_run_state(db, session)
        raise HTTPException(status_code=404, detail="Run not found")

    return StreamingResponse(
        stream_run_sse(run_id),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


@router.post("/sessions/{session_id}/messages")
async def post_message(
    session_id: uuid.UUID,
    body: ChatMessageCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> StreamingResponse:
    try:
        session = chat_svc.get_owned_session(db, user.id, session_id)
        chat_runs.ensure_session_idle(db, session)
        latest = messages_svc.latest_message(db, session)
        user_msg = messages_svc.add_message(
            db,
            session,
            role="user",
            content=body.content.strip(),
            parent_message_id=latest.id if latest is not None else None,
        )
        chat_svc.mark_session_read(db, user.id, session.id)
        db.commit()
        db.refresh(user_msg)
        db.refresh(session)
    except ServiceError as exc:
        raise_service_error(exc)

    return await _start_and_stream(user=user, session=session, user_msg=user_msg)


@router.post("/sessions/{session_id}/regenerate")
async def regenerate_message(
    session_id: uuid.UUID,
    body: MessageRegenerateRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> StreamingResponse:
    """Re-run from an existing user message — no duplicate user row."""
    try:
        target_session, user_msg = messages_svc.prepare_regenerate_target(
            db,
            user.id,
            session_id,
            user_message_id=body.user_message_id,
        )
        chat_runs.ensure_session_idle(db, target_session)
        chat_svc.mark_session_read(db, user.id, target_session.id)
        db.commit()
        db.refresh(user_msg)
        db.refresh(target_session)
    except ServiceError as exc:
        raise_service_error(exc)

    return await _start_and_stream(
        user=user, session=target_session, user_msg=user_msg
    )


@router.post("/sessions/{session_id}/messages/{message_id}/edit")
async def edit_message(
    session_id: uuid.UUID,
    message_id: uuid.UUID,
    body: MessageEditRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> StreamingResponse:
    try:
        target_session, user_msg = messages_svc.prepare_edit_target(
            db,
            user.id,
            session_id,
            message_id,
            new_content=body.content.strip(),
        )
        chat_runs.ensure_session_idle(db, target_session)
        chat_svc.mark_session_read(db, user.id, target_session.id)
        db.commit()
        db.refresh(user_msg)
        db.refresh(target_session)
    except ServiceError as exc:
        raise_service_error(exc)

    return await _start_and_stream(
        user=user, session=target_session, user_msg=user_msg
    )


@router.post("/sessions/{session_id}/ask-from-selection")
async def ask_from_selection(
    session_id: uuid.UUID,
    body: AskFromSelectionRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> StreamingResponse:
    try:
        target_session, user_msg = messages_svc.prepare_ask_from_selection(
            db,
            user.id,
            session_id,
            message_id=body.message_id,
            selected_text=body.selected_text,
            target=body.target,
            question=body.question,
        )
        chat_runs.ensure_session_idle(db, target_session)
        chat_svc.mark_session_read(db, user.id, target_session.id)
        db.commit()
        db.refresh(user_msg)
        db.refresh(target_session)
    except ServiceError as exc:
        raise_service_error(exc)

    return await _start_and_stream(
        user=user, session=target_session, user_msg=user_msg
    )
