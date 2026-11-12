"""Background chat runs: agent tiếp tục khi SSE disconnect."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select

from app.db.models import ChatSession, Message, User
from app.db.session import SessionLocal
from app.services import chat_sessions as chat_svc
from app.services.agent_run import iter_agent_events
from app.services.chat_sessions import assemble_context_messages
from app.services.errors import ConflictError, NotFoundError
from app.services.messages import add_message, messages_to_agent_history
from app.services.session_title import generate_session_title, should_autotitle

logger = logging.getLogger(__name__)

_SENTINEL: object = object()
_RUN_TTL_SECONDS = 600


@dataclass
class ChatRun:
    run_id: uuid.UUID
    session_id: uuid.UUID
    user_id: uuid.UUID
    user_message_id: uuid.UUID
    model: str | None = None  # catalog id provider:name
    history: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    subscribers: list[asyncio.Queue] = field(default_factory=list)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    task: asyncio.Task[None] | None = None
    finished: bool = False
    status: str = "running"  # running | ok | error


_runs: dict[str, ChatRun] = {}


def get_run(run_id: uuid.UUID | str) -> ChatRun | None:
    return _runs.get(str(run_id))


def _session_message_count(db, session_id: uuid.UUID) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(Message)
            .where(Message.session_id == session_id)
        )
        or 0
    )


def _persist_session_title(
    db,
    *,
    user_id: uuid.UUID,
    session: ChatSession,
    title: str,
) -> str:
    updated = chat_svc.update_session_title(
        db, user_id, session.id, title=title
    )
    db.commit()
    session.title = updated.title
    return updated.title or title


def _set_run_state(
    db,
    session_id: uuid.UUID,
    *,
    run_status: str,
    active_run_id: uuid.UUID | None,
) -> None:
    row = db.get(ChatSession, session_id)
    if row is None:
        return
    row.run_status = run_status
    row.active_run_id = active_run_id
    row.updated_at = datetime.now(UTC)
    db.add(row)
    db.commit()


def _is_run_live(run_id: uuid.UUID | None) -> bool:
    if run_id is None:
        return False
    run = _runs.get(str(run_id))
    return run is not None and not run.finished


def heal_stale_run_state(db, session: ChatSession) -> ChatSession:
    """Nếu DB nói running nhưng process không còn run → idle. Không raise.

    Trust the row already loaded for the request — no per-call refresh.
    """
    if session.run_status != "running":
        return session
    if _is_run_live(session.active_run_id):
        return session

    # Stale: clear bằng connection riêng — không commit dirty của request session.
    side = SessionLocal()
    try:
        row = side.get(ChatSession, session.id)
        if row is not None and row.run_status == "running" and not _is_run_live(
            row.active_run_id
        ):
            row.run_status = "idle"
            row.active_run_id = None
            side.add(row)
            side.commit()
            session.run_status = "idle"
            session.active_run_id = None
    finally:
        side.close()

    return session


def ensure_session_idle(db, session: ChatSession) -> None:
    """Heal stale run rồi 409 nếu vẫn đang running."""
    heal_stale_run_state(db, session)
    if session.run_status == "running":
        raise ConflictError("Session already has an active run")


async def _publish(run: ChatRun, event: str, data: dict[str, Any]) -> None:
    item = (event, data)
    async with run.lock:
        run.history.append(item)
        subscribers = list(run.subscribers)
    for queue in subscribers:
        queue.put_nowait(item)


async def _finish(run: ChatRun, *, status: str) -> None:
    run.status = status
    await _publish(run, "done", {"run_id": str(run.run_id), "status": status})
    async with run.lock:
        run.finished = True
        subscribers = list(run.subscribers)
        run.subscribers.clear()
    for queue in subscribers:
        queue.put_nowait(_SENTINEL)


async def _cleanup_later(run_id: str) -> None:
    await asyncio.sleep(_RUN_TTL_SECONDS)
    run = _runs.get(run_id)
    if run is not None and run.finished:
        _runs.pop(run_id, None)


async def _execute_run(run: ChatRun) -> None:
    db = SessionLocal()
    errored = False
    try:
        user = db.get(User, run.user_id)
        session = db.get(ChatSession, run.session_id)
        user_message = db.get(Message, run.user_message_id)
        if user is None or session is None or user_message is None:
            await _publish(
                run,
                "error",
                {"code": "not_found", "detail": "Run context missing"},
            )
            errored = True
            _set_run_state(
                db,
                run.session_id,
                run_status="error",
                active_run_id=None,
            )
            await _finish(run, status="error")
            return

        await _publish(
            run,
            "run_started",
            {
                "run_id": str(run.run_id),
                "session_id": str(session.id),
                "user_message_id": str(user_message.id),
            },
        )

        from app.services.selection_directives import expand_selection_directives

        # DB keeps chip directives for FE; agent gets plain excerpt + question.
        query = expand_selection_directives(user_message.content)
        msg_count = _session_message_count(db, session.id)
        title_task: asyncio.Task[str] | None = None
        if should_autotitle(session, message_count=msg_count):
            title_task = asyncio.create_task(
                asyncio.to_thread(generate_session_title, query)
            )

        context_rows = assemble_context_messages(db, session)
        # Only messages before this user turn (excludes prior assistant
        # siblings when regenerating the same user message).
        history_rows: list[Any] = []
        for row in context_rows:
            if row.id == user_message.id:
                break
            history_rows.append(row)
        history = messages_to_agent_history(history_rows)

        assistant_content = ""
        steps: list[dict[str, Any]] = []
        title_emitted = False

        agent_aiter = iter_agent_events(
            query=query,
            user_id=str(user.id),
            history=history,
            run_id=str(run.run_id),
            session_id=str(run.session_id),
            model=run.model,
        ).__aiter__()
        next_agent: asyncio.Task[Any] = asyncio.create_task(
            agent_aiter.__anext__()
        )
        pending: set[asyncio.Task[Any]] = {next_agent}
        if title_task is not None:
            pending.add(title_task)

        while pending:
            done, pending = await asyncio.wait(
                pending, return_when=asyncio.FIRST_COMPLETED
            )
            for task in done:
                if title_task is not None and task is title_task:
                    if not title_emitted:
                        try:
                            title = task.result()
                        except Exception:  # noqa: BLE001
                            title = None
                        if title:
                            saved = _persist_session_title(
                                db,
                                user_id=user.id,
                                session=session,
                                title=title,
                            )
                            await _publish(
                                run,
                                "session_updated",
                                {
                                    "session_id": str(session.id),
                                    "title": saved,
                                },
                            )
                        title_emitted = True
                    continue

                try:
                    evt = task.result()
                except StopAsyncIteration:
                    continue

                name = evt["event"]
                data = evt.get("data") or {}
                if name == "message_completed":
                    assistant_content = str(data.get("content") or "")
                    steps = list(data.get("steps") or [])
                    # Don't persist empty stubs — they break regenerate hydrate
                    # (U → empty A → duplicate U).
                    if not assistant_content.strip():
                        data = {
                            "assistant_message_id": None,
                            "content": "",
                        }
                        await _publish(run, name, data)
                        continue
                    assistant_meta: dict[str, Any] = {
                        "run_id": str(run.run_id),
                        "steps": steps,
                    }
                    if run.model:
                        assistant_meta["model"] = run.model
                    assistant = add_message(
                        db,
                        session,
                        role="assistant",
                        content=assistant_content,
                        metadata=assistant_meta,
                        parent_message_id=user_message.id,
                    )
                    chat_svc.touch_session(db, session)
                    db.commit()
                    data = {
                        "assistant_message_id": str(assistant.id),
                        "content": assistant_content,
                    }
                    await _publish(run, name, data)
                elif name == "error":
                    errored = True
                    db.rollback()
                    await _publish(run, name, data)
                else:
                    await _publish(run, name, data)

                next_agent = asyncio.create_task(agent_aiter.__anext__())
                pending.add(next_agent)

        final_status = "error" if errored else "ok"
        _set_run_state(
            db,
            run.session_id,
            run_status="error" if errored else "completed",
            active_run_id=None,
        )
        await _finish(run, status=final_status)
    except Exception as exc:  # noqa: BLE001
        logger.exception("chat run failed: %s", run.run_id)
        try:
            db.rollback()
        except Exception:  # noqa: BLE001
            pass
        try:
            await _publish(
                run,
                "error",
                {"code": "internal", "detail": str(exc)},
            )
        except Exception:  # noqa: BLE001
            pass
        try:
            _set_run_state(
                db,
                run.session_id,
                run_status="error",
                active_run_id=None,
            )
        except Exception:  # noqa: BLE001
            pass
        if not run.finished:
            await _finish(run, status="error")
    finally:
        db.close()
        asyncio.create_task(_cleanup_later(str(run.run_id)))


async def start_chat_run(
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    user_message_id: uuid.UUID,
    model: str | None = None,
) -> uuid.UUID:
    """Bắt đầu agent run nền. Raise ConflictError nếu session đang chạy."""
    db = SessionLocal()
    try:
        session = db.scalar(
            select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id,
            )
        )
        if session is None:
            raise NotFoundError("Chat session not found")
        ensure_session_idle(db, session)

        run_id = uuid.uuid4()
        run = ChatRun(
            run_id=run_id,
            session_id=session_id,
            user_id=user_id,
            user_message_id=user_message_id,
            model=(model or "").strip() or None,
        )
        _runs[str(run_id)] = run
        _set_run_state(
            db,
            session_id,
            run_status="running",
            active_run_id=run_id,
        )
    finally:
        db.close()

    run.task = asyncio.create_task(_execute_run(run))
    return run.run_id


async def iter_run_events(
    run_id: uuid.UUID | str,
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    """Replay history rồi theo live events đến khi run xong."""
    run = get_run(run_id)
    if run is None:
        raise NotFoundError("Run not found")

    queue: asyncio.Queue = asyncio.Queue()
    async with run.lock:
        snapshot = list(run.history)
        live = not run.finished
        if live:
            run.subscribers.append(queue)

    for event, data in snapshot:
        yield event, data

    if not live:
        return

    try:
        while True:
            item = await queue.get()
            if item is _SENTINEL:
                break
            event, data = item
            yield event, data
    finally:
        async with run.lock:
            if queue in run.subscribers:
                run.subscribers.remove(queue)
