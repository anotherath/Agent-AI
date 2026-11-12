"""Helper chọn đúng một tool + args (LLM structured output + retry)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, create_model

from agent.config import get_tool_select_max_retries
from agent.models import get_chat_model
from agent.prompts.tool_select import TOOL_SELECT_SYSTEM, TOOL_SELECT_USER
from agent.state import ToolPick
from agent.tools.registry import (
    NO_TOOL_NAME,
    is_no_tool,
    known_tool_names_sorted,
    resolve_tool_name,
    resolve_tool_select_name,
    tool_catalog_text,
    tool_select_catalog_text,
    tool_select_names_sorted,
)

# Số tin gần nhất đưa vào pick (tránh phình context).
TOOL_SELECT_HISTORY_LIMIT = 6


def _tool_pick_schema(*, allow_no_tool: bool) -> type[BaseModel]:
    """Schema enum: tool_select (+ no_tool) hoặc rematch plan (chỉ tool thật)."""
    names = tuple(
        tool_select_names_sorted() if allow_no_tool else known_tool_names_sorted()
    )
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
    allow_no_tool: bool = True,
) -> ToolPick:
    """Chọn 1 tool. allow_no_tool=True chỉ cho tool_select; rematch plan → False."""
    schema = _tool_pick_schema(allow_no_tool=allow_no_tool)
    llm = get_chat_model().with_structured_output(schema)
    if allow_no_tool:
        allowed = ", ".join(tool_select_names_sorted()) or "(không có)"
        catalog = tool_select_catalog_text()
    else:
        allowed = ", ".join(known_tool_names_sorted()) or "(không có)"
        catalog = tool_catalog_text()
    system = TOOL_SELECT_SYSTEM.format(tool_catalog=catalog)
    user = TOOL_SELECT_USER.format(
        query=query,
        recent_messages=_format_recent_messages(messages, limit=history_limit),
    )
    max_retries = get_tool_select_max_retries()

    def _accept(picked: ToolPick) -> ToolPick | None:
        if allow_no_tool:
            resolved = resolve_tool_select_name(picked.tool_name)
            if resolved is None:
                return None
            if is_no_tool(resolved):
                return ToolPick(
                    tool_name=NO_TOOL_NAME,
                    tool_args={},
                    reason=picked.reason or "no_tool",
                )
            return ToolPick(
                tool_name=resolved,
                tool_args=picked.tool_args or {},
                reason=picked.reason or "",
            )
        resolved = resolve_tool_name(picked.tool_name)
        if resolved is None:
            return None
        return ToolPick(
            tool_name=resolved,
            tool_args=picked.tool_args or {},
            reason=picked.reason or "",
        )

    try:
        result = llm.invoke(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ]
        )
    except Exception as exc:  # noqa: BLE001
        return ToolPick(tool_name="", reason=f"pick_failed: {exc}")

    picked = _parse_pick(result)
    accepted = _accept(picked)
    if accepted is not None:
        return accepted

    bad = (picked.tool_name or "").strip() or "(trống)"
    for _ in range(max_retries):
        retry_user = (
            f"{user}\n\n"
            f"Lỗi: tool_name `{bad}` không hợp lệ hoặc trống. "
            f"Bắt buộc chọn đúng một tên trong: {allowed}."
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
        accepted2 = _accept(picked2)
        if accepted2 is not None:
            return accepted2
        bad = (picked2.tool_name or "").strip() or "(trống)"

    return ToolPick(
        tool_name="",
        tool_args={},
        reason=f"pick_invalid_name:{bad}",
    )


__all__ = ["pick_single_tool", "TOOL_SELECT_HISTORY_LIMIT"]
