"""Node tool_execution — gọi đúng 1 tool từ tool_pick (sau tool_select)."""

from __future__ import annotations

import json
from typing import Any

from agent.nodes.util.tool_invocation import invoke_named_tool
from agent.state import AgentState
from agent.tools.registry import (
    is_no_tool,
    known_tool_names_sorted,
    no_tool_result,
    resolve_tool_name,
)


def tool_execution_node(state: AgentState) -> dict[str, Any]:
    query = state.get("query") or ""
    tool_results = list(state.get("tool_results") or [])
    step = len(tool_results)
    pick = state.get("tool_pick")

    tool_name = pick.tool_name if pick is not None else None
    tool_args = pick.tool_args if pick is not None else None

    if is_no_tool(tool_name):
        reason = ""
        if pick is not None:
            reason = (pick.reason or "").strip()
        tool_results.append(no_tool_result(step=step, reason=reason))
        return {"tool_results": tool_results, "step_index": step}

    resolved = resolve_tool_name(tool_name)

    if resolved is None:
        raw_name = (tool_name or "").strip() or "(invalid)"
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


__all__ = ["tool_execution_node"]
