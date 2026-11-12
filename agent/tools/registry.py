"""Lookup tool theo tên + catalog mô tả cho routing/planner."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from langchain_core.tools import BaseTool

from agent.tools import get_tools

if TYPE_CHECKING:
    from agent.state import PlanStep, ReviewDecision, RouteDecision

# Sentinel chỉ cho nhánh tool_select (không dùng trong planner).
NO_TOOL_NAME = "no_tool"
NO_TOOL_DESCRIPTION = (
    "Không gọi tool nào. Dùng khi đã vào nhánh chọn tool nhưng query không cần "
    "tool (tránh để trống hoặc chọn bừa). Không phải tool API thật."
)


@lru_cache(maxsize=1)
def get_tool_map() -> dict[str, BaseTool]:
    return {t.name: t for t in get_tools()}


def get_tool(name: str) -> BaseTool:
    tool = get_tool_map().get(name)
    if tool is None:
        raise KeyError(f"Unknown tool: {name}")
    return tool


def known_tool_names() -> set[str]:
    return set(get_tool_map().keys())


def known_tool_names_sorted() -> list[str]:
    return sorted(known_tool_names())


def is_no_tool(name: str | None) -> bool:
    return bool(name) and name.strip() == NO_TOOL_NAME


def tool_select_names_sorted() -> list[str]:
    """Tên được chọn ở tool_select: registry + no_tool."""
    return [*known_tool_names_sorted(), NO_TOOL_NAME]


def resolve_tool_name(name: str | None) -> str | None:
    """Exact match với registry thật; sai / trống / no_tool → None."""
    if not name:
        return None
    key = name.strip()
    if not key or key == NO_TOOL_NAME:
        return None
    return key if key in get_tool_map() else None


def resolve_tool_select_name(name: str | None) -> str | None:
    """Registry thật hoặc no_tool (chỉ nhánh tool_select)."""
    if is_no_tool(name):
        return NO_TOOL_NAME
    return resolve_tool_name(name)


sanitize_tool_name = resolve_tool_name


def sanitize_plan_steps(steps: list[PlanStep] | None) -> list[PlanStep]:
    """Clear tool_name/args trên bước có tên ngoài registry (no_tool cũng bị clear)."""
    if not steps:
        return []
    out: list[PlanStep] = []
    for step in steps:
        resolved = resolve_tool_name(step.tool_name)
        if resolved is None:
            out.append(step.model_copy(update={"tool_name": "", "tool_args": {}}))
        elif resolved != step.tool_name:
            out.append(step.model_copy(update={"tool_name": resolved}))
        else:
            out.append(step)
    return out


def sanitize_route_decision(decision: RouteDecision) -> RouteDecision:
    """RouteDecision chỉ còn nhánh — giữ API cũ, không sửa field tool."""
    return decision


def sanitize_review_decision(decision: ReviewDecision) -> ReviewDecision:
    """Drop hallucinated tool_name; giữ no_tool cho tool_select."""
    if is_no_tool(decision.tool_name):
        return decision.model_copy(
            update={"tool_name": NO_TOOL_NAME, "tool_args": {}}
        )
    resolved = resolve_tool_name(decision.tool_name)
    if decision.tool_name and resolved is None:
        return decision.model_copy(update={"tool_name": None, "tool_args": None})
    if resolved is not None and resolved != decision.tool_name:
        return decision.model_copy(update={"tool_name": resolved})
    return decision


def no_tool_result(*, step: int, reason: str = "") -> dict[str, Any]:
    """ToolResult khi tool_select chọn no_tool (không gọi API)."""
    payload = {"skipped": True, "reason": reason or "no_tool"}
    return {
        "step": step,
        "tool": NO_TOOL_NAME,
        "args": {},
        "result": json.dumps(payload, ensure_ascii=False),
        "ok": True,
    }


def tool_catalog_text() -> str:
    """Catalog tool thật — planner / orchestrator (không gồm no_tool)."""
    blocks: list[str] = []
    for tool in get_tools():
        desc = (tool.description or "").strip()
        if desc:
            blocks.append(f"- {tool.name}:\n{desc}")
        else:
            blocks.append(f"- {tool.name}")
    return "\n\n".join(blocks) if blocks else "(không có tool)"


def tool_select_catalog_text() -> str:
    """Catalog cho tool_select: tool thật + sentinel no_tool."""
    base = tool_catalog_text()
    line = f"- {NO_TOOL_NAME}:\n{NO_TOOL_DESCRIPTION}"
    if base == "(không có tool)":
        return line
    return f"{base}\n\n{line}"


def tool_result_paths_text() -> str:
    """Catalog path `$stepN.*` của tool đang đăng ký — tách khỏi description."""
    from agent.tools.result_paths import tool_result_paths_text as _paths_text

    return _paths_text()


def clear_tool_map_cache() -> None:
    get_tool_map.cache_clear()


__all__ = [
    "NO_TOOL_NAME",
    "NO_TOOL_DESCRIPTION",
    "get_tool_map",
    "get_tool",
    "known_tool_names",
    "known_tool_names_sorted",
    "is_no_tool",
    "tool_select_names_sorted",
    "resolve_tool_name",
    "resolve_tool_select_name",
    "sanitize_tool_name",
    "sanitize_plan_steps",
    "sanitize_route_decision",
    "sanitize_review_decision",
    "no_tool_result",
    "tool_catalog_text",
    "tool_select_catalog_text",
    "tool_result_paths_text",
    "clear_tool_map_cache",
]
