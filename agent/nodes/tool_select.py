"""Node tool_select — chọn đúng 1 tool + args, ghi tool_pick vào state."""

from __future__ import annotations

from typing import Any

from agent.nodes.util.tool_pick import pick_single_tool
from agent.state import AgentState, ToolPick
from agent.tools.registry import (
    NO_TOOL_NAME,
    is_no_tool,
    resolve_tool_select_name,
)


def tool_select_node(state: AgentState) -> dict[str, Any]:
    """Chọn tool cho nhánh single_tool; ghi tool_pick vào state."""
    query = state.get("query") or ""
    review = state.get("review")

    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None
    reason = ""
    if review is not None and getattr(review, "next", None) == "single_tool":
        tool_name = review.tool_name
        tool_args = review.tool_args
        reason = review.reason or "from_review"

    resolved = resolve_tool_select_name(tool_name)
    if resolved is not None:
        if is_no_tool(resolved):
            return {
                "tool_pick": ToolPick(
                    tool_name=NO_TOOL_NAME,
                    tool_args={},
                    reason=reason or "no_tool",
                )
            }
        return {
            "tool_pick": ToolPick(
                tool_name=resolved,
                tool_args=tool_args or {},
                reason=reason or "from_review",
            )
        }

    picked = pick_single_tool(query, state.get("messages"))
    return {"tool_pick": picked}


__all__ = ["tool_select_node"]
