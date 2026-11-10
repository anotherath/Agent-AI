"""Langfuse tracing helpers for LangGraph runs.

Env (loaded before client init):
  LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_BASE_URL
  LANGFUSE_TRACING_ENVIRONMENT  optional (development|staging|production)
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from dotenv import load_dotenv

load_dotenv()

_ENABLED: bool | None = None
DEFAULT_TAGS = ["chat", "langgraph"]


def langfuse_enabled() -> bool:
    """True when both API keys are set (tracing is opt-in via env)."""
    global _ENABLED
    if _ENABLED is None:
        _ENABLED = bool(
            os.getenv("LANGFUSE_PUBLIC_KEY", "").strip()
            and os.getenv("LANGFUSE_SECRET_KEY", "").strip()
        )
    return _ENABLED


def get_langfuse_client():
    """Return Langfuse client after env is loaded. None when disabled."""
    if not langfuse_enabled():
        return None
    from langfuse import get_client

    return get_client()


@contextmanager
def chat_turn_trace(
    *,
    query: str,
    user_id: str,
    session_id: str | None = None,
    run_id: str | None = None,
) -> Iterator[dict[str, Any]]:
    """Open a ``chat-turn`` root span and yield LangGraph runnable ``config``.

    One chat turn = one trace; ``session_id`` groups turns into a Langfuse session.
    Root input/output are set to the user message / assistant answer (not full state).
    Yields ``{"config": {...}, "root": span_or_none}``.
    """
    if not langfuse_enabled():
        yield {"config": {}, "root": None}
        return

    from langfuse import propagate_attributes
    from langfuse.langchain import CallbackHandler

    langfuse = get_langfuse_client()
    assert langfuse is not None

    tags = list(DEFAULT_TAGS)
    meta: dict[str, str] = {}
    if run_id:
        meta["agent_run_id"] = run_id

    with langfuse.start_as_current_observation(
        as_type="agent",
        name="chat-turn",
    ) as root:
        # Trace-level I/O: chatbot turn (role-labeled messages for Sessions UI).
        root.update(input=[{"role": "user", "content": query}])

        prop_kwargs: dict[str, Any] = {
            "user_id": user_id,
            "tags": tags,
        }
        if session_id:
            prop_kwargs["session_id"] = session_id
        if meta:
            prop_kwargs["metadata"] = meta

        with propagate_attributes(**prop_kwargs):
            config: dict[str, Any] = {
                "callbacks": [CallbackHandler()],
                "run_name": "langgraph",
                "tags": tags,
                "metadata": {
                    "langfuse_user_id": user_id,
                    "langfuse_tags": tags,
                    **({"langfuse_session_id": session_id} if session_id else {}),
                    **meta,
                },
            }
            ctx = {"config": config, "root": root}
            try:
                yield ctx
            finally:
                answer = ctx.get("answer")
                if isinstance(answer, str) and answer:
                    root.update(
                        output=[{"role": "assistant", "content": answer}]
                    )


def flush_langfuse() -> None:
    """Flush pending spans (call on process shutdown / after short scripts)."""
    client = get_langfuse_client()
    if client is not None:
        client.flush()


__all__ = [
    "langfuse_enabled",
    "get_langfuse_client",
    "chat_turn_trace",
    "flush_langfuse",
    "DEFAULT_TAGS",
]
