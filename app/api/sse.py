"""SSE helpers for chat agent streams."""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from typing import Any

from app.services.chat_runs import iter_run_events
from app.services.errors import NotFoundError


def _sse_pack(event: str, data: dict[str, Any]) -> str:
    payload = json.dumps(data, default=str, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


async def stream_run_sse(run_id: uuid.UUID | str) -> AsyncIterator[str]:
    """Consumer SSE cho một background run (replay + live)."""
    try:
        async for event, data in iter_run_events(run_id):
            yield _sse_pack(event, data)
    except NotFoundError:
        yield _sse_pack(
            "error",
            {"code": "run_not_found", "detail": "Run not found"},
        )
        yield _sse_pack(
            "done",
            {"run_id": str(run_id), "status": "error"},
        )
