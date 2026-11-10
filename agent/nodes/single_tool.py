"""Node single_tool — gọi đúng 1 tool từ route hoặc review."""

from __future__ import annotations

import json
from typing import Any

from agent.nodes.tool_invoke import invoke_named_tool
from agent.nodes.tool_select import pick_single_tool
from agent.state import AgentState
from agent.tools.registry import known_tool_names_sorted, resolve_tool_name


def single_tool_node(state: AgentState) -> dict[str, Any]:
    query = state.get("query") or ""
    tool_results = list(state.get("tool_results") or [])
    step = len(tool_results)

    review = state.get("review")
    route = state.get("route")

    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None
    if review is not None and getattr(review, "next", None) == "single_tool":
        tool_name = review.tool_name
        tool_args = review.tool_args
    elif route is not None:
        tool_name = route.tool_name
        tool_args = route.tool_args

    resolved = resolve_tool_name(tool_name)
    if resolved is None:
        picked = pick_single_tool(query, state.get("messages"))
        resolved = resolve_tool_name(picked.tool_name)
        tool_args = picked.tool_args or tool_args
        if resolved is None:
            raw_name = (picked.tool_name or "").strip() or "(invalid)"
            available = ", ".join(known_tool_names_sorted()) or "(none)"
            tool_results.append(
                {
                    "step": step,
                    "tool": raw_name,
                    "args": tool_args or {},
                    "result": json.dumps(
                        {
                            "error": (
                                f"Unknown tool: {raw_name}. "
                                f"Available tools: {available}"
                            ),
                        },
                        ensure_ascii=False,
                    ),
                    "ok": False,
                }
            )
            return {"tool_results": tool_results, "step_index": step}

    entry = invoke_named_tool(
        tool_name=resolved,
        tool_args=tool_args,
        query=query,
        tool_results=tool_results,
        step=step,
    )
    tool_results.append(entry)
    return {"tool_results": tool_results, "step_index": step}
