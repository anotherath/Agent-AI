"""Khi Jev chỉ chọn single_tool mà chưa có tool_name — LLM chọn tool + args."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, create_model

from agent.models import get_chat_model
from agent.prompts.tool_select import TOOL_SELECT_SYSTEM, TOOL_SELECT_USER
from agent.tools.registry import (
    known_tool_names_sorted,
    resolve_tool_name,
    tool_catalog_text,
)

# Số tin gần nhất đưa vào pick (tránh phình context).
TOOL_SELECT_HISTORY_LIMIT = 6


class ToolPick(BaseModel):
    tool_name: str
    tool_args: dict[str, Any] = Field(default_factory=dict)
    reason: str = ""


def _tool_pick_schema() -> type[BaseModel]:
    """Structured-output schema với tool_name ∈ registry (enum động)."""
    names = tuple(known_tool_names_sorted())
    if not names:
        return ToolPick
    name_type = Literal[*names]  # type: ignore[valid-type]
    return create_model(
        "ToolPickConstrained",
        tool_name=(name_type, ...),
        tool_args=(dict[str, Any], Field(default_factory=dict)),
        reason=(str, ""),
        __base__=BaseModel,
    )


def _format_recent_messages(messages: list | None, *, limit: int) -> str:
    if not messages:
        return "(không có)"
    tail = list(messages)[-max(1, limit) :]
    lines: list[str] = []
    for msg in tail:
        if not isinstance(msg, dict):
            continue
        role = str(msg.get("role") or "").strip() or "?"
        content = str(msg.get("content") or "").strip()
        if not content:
            continue
        # Cắt bớt tin quá dài (đặc biệt assistant).
        if len(content) > 500:
            content = content[:500] + "…"
        lines.append(f"- {role}: {content}")
    return "\n".join(lines) if lines else "(không có)"


def _parse_pick(result: Any) -> ToolPick:
    if isinstance(result, ToolPick):
        return result
    if result is None:
        return ToolPick(tool_name="", reason="structured_output_none")
    if isinstance(result, BaseModel):
        try:
            return ToolPick.model_validate(result.model_dump())
        except Exception as exc:  # noqa: BLE001
            return ToolPick(tool_name="", reason=f"pick_invalid: {exc}")
    try:
        return ToolPick.model_validate(result)
    except Exception as exc:  # noqa: BLE001
        return ToolPick(tool_name="", reason=f"pick_invalid: {exc}")


def pick_single_tool(
    query: str,
    messages: list | None = None,
    *,
    history_limit: int = TOOL_SELECT_HISTORY_LIMIT,
) -> ToolPick:
    schema = _tool_pick_schema()
    llm = get_chat_model().with_structured_output(schema)
    allowed = ", ".join(known_tool_names_sorted()) or "(không có)"
    system = TOOL_SELECT_SYSTEM.format(tool_catalog=tool_catalog_text())
    user = TOOL_SELECT_USER.format(
        query=query,
        recent_messages=_format_recent_messages(messages, limit=history_limit),
    )
    chat = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    try:
        result = llm.invoke(chat)
    except Exception as exc:  # noqa: BLE001 — provider/structured output fail
        return ToolPick(tool_name="", reason=f"pick_failed: {exc}")

    picked = _parse_pick(result)
    if resolve_tool_name(picked.tool_name):
        return picked

    # structured output None / parse fail — không retry vô ích.
    if not (picked.tool_name or "").strip():
        return picked

    # Provider bỏ qua enum → một lần retry kèm danh sách hợp lệ.
    bad = picked.tool_name.strip()
    retry_user = (
        f"{user}\n\n"
        f"Lỗi: `{bad}` không phải tool hợp lệ. "
        f"Chỉ được chọn đúng một tên trong: {allowed}."
    )
    try:
        result2 = llm.invoke(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": retry_user},
            ]
        )
    except Exception as exc:  # noqa: BLE001
        return ToolPick(tool_name="", reason=f"pick_retry_failed: {exc}")

    picked2 = _parse_pick(result2)
    if resolve_tool_name(picked2.tool_name):
        return picked2
    # Không trả tên bịa — để single_tool soft-fail sạch.
    return ToolPick(
        tool_name="",
        tool_args={},
        reason=f"pick_invalid_name:{bad}",
    )


__all__ = ["ToolPick", "pick_single_tool", "TOOL_SELECT_HISTORY_LIMIT"]
