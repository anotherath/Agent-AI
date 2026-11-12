"""Node plan_execution — chạy plan tuần tự + resolve $stepN + rematch từng bước."""

from __future__ import annotations

import json
from typing import Any

from agent.config import get_planner_max_retries
from agent.nodes.util.step_rematch import (
    is_args_failure,
    precheck_step_args,
    rematch_step_args,
    rematch_step_pick,
)
from agent.nodes.util.tool_invocation import invoke_named_tool
from agent.nodes.util.tool_pick import pick_single_tool
from agent.state import AgentState, PlanStep
from agent.tools.registry import known_tool_names_sorted, resolve_tool_name


def _soft_fail(
    *,
    step_idx: int,
    tool_label: str,
    tool_args: dict[str, Any] | None,
    error: str,
    purpose: str = "",
) -> dict[str, Any]:
    payload: dict[str, Any] = {"error": error}
    if purpose:
        payload["purpose"] = purpose
    return {
        "step": step_idx,
        "tool": tool_label,
        "args": tool_args or {},
        "result": json.dumps(payload, ensure_ascii=False),
        "ok": False,
    }


def _run_step_with_rematch(
    *,
    query: str,
    step: PlanStep,
    step_idx: int,
    tool_results: list,
    messages: list | None,
    max_retries: int,
) -> dict[str, Any]:
    """Chạy một bước; mỗi lỗi args/tên được sửa tối đa max_retries lần."""
    tool_name = resolve_tool_name(step.tool_name)
    tool_args: dict[str, Any] | None = dict(step.tool_args or {})
    name_retries = 0
    args_retries = 0

    while True:
        if tool_name is None:
            if name_retries >= max_retries:
                available = ", ".join(known_tool_names_sorted()) or "(none)"
                raw = (step.tool_name or "").strip() or "(invalid)"
                return _soft_fail(
                    step_idx=step_idx,
                    tool_label=raw,
                    tool_args=tool_args,
                    error=(
                        f"Unknown tool: {raw}. Available tools: {available}"
                    ),
                    purpose=step.purpose or "",
                )
            tool_name, tool_args = rematch_step_pick(
                query=query,
                step=step,
                messages=messages,
                pick_single_tool=pick_single_tool,
            )
            name_retries += 1
            continue

        pre_err = precheck_step_args(
            tool_name=tool_name,
            tool_args=tool_args,
            tool_results=tool_results,
        )
        if pre_err:
            if args_retries >= max_retries:
                return _soft_fail(
                    step_idx=step_idx,
                    tool_label=tool_name,
                    tool_args=tool_args,
                    error=pre_err,
                    purpose=step.purpose or "",
                )
            tool_args = rematch_step_args(
                query=query,
                step=step,
                tool_name=tool_name,
                previous_args=tool_args,
                tool_results=tool_results,
                error=pre_err,
            )
            args_retries += 1
            continue

        entry = invoke_named_tool(
            tool_name=tool_name,
            tool_args=tool_args,
            query=query,
            tool_results=tool_results,
            step=step_idx,
        )
        if entry.get("ok"):
            return entry

        raw = entry.get("result")
        if is_args_failure(raw) and args_retries < max_retries:
            tool_args = rematch_step_args(
                query=query,
                step=step,
                tool_name=tool_name,
                previous_args=entry.get("args") or tool_args,
                tool_results=tool_results,
                error=str(raw),
            )
            args_retries += 1
            continue

        return entry


def plan_execution_node(state: AgentState) -> dict[str, Any]:
    query = state.get("query") or ""
    plan: list[PlanStep] = list(state.get("plan") or [])
    tool_results = list(state.get("tool_results") or [])
    messages = state.get("messages")
    base_step = len(tool_results)
    max_retries = get_planner_max_retries()

    for offset, step in enumerate(plan):
        step_idx = base_step + offset
        entry = _run_step_with_rematch(
            query=query,
            step=step,
            step_idx=step_idx,
            tool_results=tool_results,
            messages=messages,
            max_retries=max_retries,
        )
        tool_results.append(entry)

    return {
        "tool_results": tool_results,
        "step_index": len(tool_results),
    }


__all__ = ["plan_execution_node"]
