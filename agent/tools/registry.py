"""Lookup tool theo tên + catalog mô tả cho routing/planner."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from langchain_core.tools import BaseTool

from agent.tools import get_tools

if TYPE_CHECKING:
    from agent.state import PlanStep, ReviewDecision, RouteDecision


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


def resolve_tool_name(name: str | None) -> str | None:
    """Exact match với registry; sai / trống → None."""
    if not name:
        return None
    key = name.strip()
    if not key:
        return None
    return key if key in get_tool_map() else None


sanitize_tool_name = resolve_tool_name


def sanitize_plan_steps(steps: list[PlanStep] | None) -> list[PlanStep]:
    """Clear tool_name/args trên bước có tên ngoài registry."""
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
    """Drop hallucinated tool_name; keep route. Sanitize nested plan steps."""
    updates: dict = {}
    if decision.route == "direct":
        updates["tool_name"] = None
        updates["tool_args"] = None
    else:
        resolved = resolve_tool_name(decision.tool_name)
        if decision.tool_name and resolved is None:
            updates["tool_name"] = None
            updates["tool_args"] = None
        elif resolved is not None and resolved != decision.tool_name:
            updates["tool_name"] = resolved
    if decision.plan:
        updates["plan"] = sanitize_plan_steps(decision.plan)
    if not updates:
        return decision
    return decision.model_copy(update=updates)


def sanitize_review_decision(decision: ReviewDecision) -> ReviewDecision:
    """Drop hallucinated tool_name on review decisions."""
    resolved = resolve_tool_name(decision.tool_name)
    if decision.tool_name and resolved is None:
        return decision.model_copy(update={"tool_name": None, "tool_args": None})
    if resolved is not None and resolved != decision.tool_name:
        return decision.model_copy(update={"tool_name": resolved})
    return decision


def tool_catalog_text() -> str:
    """Full tool.description — dùng để chọn đúng tool (không cắt dòng đầu)."""
    blocks: list[str] = []
    for tool in get_tools():
        desc = (tool.description or "").strip()
        if desc:
            blocks.append(f"- {tool.name}:\n{desc}")
        else:
            blocks.append(f"- {tool.name}")
    return "\n\n".join(blocks) if blocks else "(không có tool)"


def clear_tool_map_cache() -> None:
    get_tool_map.cache_clear()


__all__ = [
    "get_tool_map",
    "get_tool",
    "known_tool_names",
    "known_tool_names_sorted",
    "resolve_tool_name",
    "sanitize_tool_name",
    "sanitize_plan_steps",
    "sanitize_route_decision",
    "sanitize_review_decision",
    "tool_catalog_text",
    "clear_tool_map_cache",
]
