"""Node execute_plan — chạy plan tuần tự + resolve $stepN."""

from __future__ import annotations

import json
from typing import Any

from agent.nodes.tool_invoke import invoke_named_tool
from agent.nodes.tool_select import pick_single_tool
from agent.state import AgentState, PlanStep
from agent.tools.registry import known_tool_names_sorted, resolve_tool_name


def _rematch_step(
    *,
    query: str,
    step: PlanStep,
    messages: list | None,
) -> tuple[str | None, dict[str, Any] | None]:
    """Khi plan bịa/để trống tool_name — pick lại từ registry (như single_tool)."""
    purpose = (step.purpose or "").strip()
    pick_query = f"{query}\nBước cần làm: {purpose}" if purpose else query
    picked = pick_single_tool(pick_query, messages)
    resolved = resolve_tool_name(picked.tool_name)
    args = picked.tool_args or step.tool_args or {}
    return resolved, args


def execute_plan_node(state: AgentState) -> dict[str, Any]:
    query = state.get("query") or ""
    plan: list[PlanStep] = list(state.get("plan") or [])
    tool_results = list(state.get("tool_results") or [])
    messages = state.get("messages")
    # Bước mới tiếp nối index hiện có (replan có thể đã có results cũ)
    base_step = len(tool_results)

    for offset, step in enumerate(plan):
        step_idx = base_step + offset
        tool_name = resolve_tool_name(step.tool_name)
        tool_args: dict[str, Any] | None = step.tool_args

        if tool_name is None:
            tool_name, tool_args = _rematch_step(
                query=query, step=step, messages=messages
            )

        if tool_name is None:
            available = ", ".join(known_tool_names_sorted()) or "(none)"
            raw = (step.tool_name or "").strip() or "(invalid)"
            tool_results.append(
                {
                    "step": step_idx,
                    "tool": raw,
                    "args": tool_args or {},
                    "result": json.dumps(
                        {
                            "error": (
                                f"Unknown tool: {raw}. "
                                f"Available tools: {available}"
                            ),
                            "purpose": step.purpose or "",
                        },
                        ensure_ascii=False,
                    ),
                    "ok": False,
                }
            )
            continue

        entry = invoke_named_tool(
            tool_name=tool_name,
            tool_args=tool_args,
            query=query,
            tool_results=tool_results,
            step=step_idx,
        )
        tool_results.append(entry)

    return {
        "tool_results": tool_results,
        "step_index": len(tool_results),
    }
