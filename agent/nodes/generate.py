"""Node generate — LLM tổng hợp answer (async stream để SSE không bị block)."""

from __future__ import annotations

import json
from typing import Any

from agent.models import get_chat_model, resolve_generate_max_tokens
from agent.prompts.generate import GENERATE_SYSTEM, GENERATE_USER
from agent.state import AgentState


def _chunk_text(chunk: Any) -> str:
    content = getattr(chunk, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
            else:
                parts.append(str(block))
        return "".join(parts)
    if content is None:
        return ""
    return str(content)


def build_generate_messages(
    state: AgentState,
    *,
    max_tokens: int,
) -> list[dict[str, str]]:
    query = state.get("query") or ""
    tool_results = state.get("tool_results") or []
    documents = state.get("documents") or []
    user = GENERATE_USER.format(
        query=query,
        tool_results=json.dumps(tool_results, ensure_ascii=False, default=str),
        documents=json.dumps(documents, ensure_ascii=False, default=str),
    )
    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": GENERATE_SYSTEM.format(max_tokens=max_tokens),
        },
    ]
    for msg in state.get("messages") or []:
        if isinstance(msg, dict) and "role" in msg and "content" in msg:
            messages.append(
                {"role": str(msg["role"]), "content": str(msg["content"])}
            )
    messages.append({"role": "user", "content": user})
    return messages


async def generate_node(state: AgentState) -> dict[str, Any]:
    """Async để astream_events/SSE yield từng token, không block event loop."""
    max_tokens = resolve_generate_max_tokens()
    llm = get_chat_model(max_tokens=max_tokens)
    messages = build_generate_messages(state, max_tokens=max_tokens)
    parts: list[str] = []
    async for chunk in llm.astream(messages):
        text = _chunk_text(chunk)
        if text:
            parts.append(text)
    return {"answer": "".join(parts).strip()}
