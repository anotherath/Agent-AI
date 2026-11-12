"""Sentinel no_tool — chỉ nhánh tool_select / tool_execution."""

from __future__ import annotations

import json

from agent.nodes.tool_execution import tool_execution_node
from agent.nodes.tool_select import tool_select_node
from agent.state import ReviewDecision, ToolPick, initial_state
from agent.tools.registry import (
    NO_TOOL_NAME,
    is_no_tool,
    resolve_tool_name,
    resolve_tool_select_name,
    sanitize_plan_steps,
    tool_catalog_text,
    tool_select_catalog_text,
)
from agent.state import PlanStep


def test_no_tool_resolve_select_only() -> None:
    assert is_no_tool(NO_TOOL_NAME)
    assert resolve_tool_name(NO_TOOL_NAME) is None
    assert resolve_tool_select_name(NO_TOOL_NAME) == NO_TOOL_NAME
    assert NO_TOOL_NAME not in tool_catalog_text()
    assert NO_TOOL_NAME in tool_select_catalog_text()


def test_sanitize_plan_clears_no_tool() -> None:
    steps = sanitize_plan_steps(
        [PlanStep(tool_name=NO_TOOL_NAME, tool_args={}, purpose="x")]
    )
    assert steps[0].tool_name == ""


def test_tool_select_accepts_no_tool_from_review() -> None:
    state = initial_state("chào")
    state["review"] = ReviewDecision(
        next="single_tool",
        tool_name=NO_TOOL_NAME,
        tool_args={},
        reason="không cần",
        decided_by="llm",
    )
    out = tool_select_node(state)
    assert out["tool_pick"].tool_name == NO_TOOL_NAME
    assert out["tool_pick"].tool_args == {}


def test_tool_execution_skips_no_tool() -> None:
    state = initial_state("xin chào")
    state["tool_pick"] = ToolPick(
        tool_name=NO_TOOL_NAME, tool_args={}, reason="skip"
    )
    out = tool_execution_node(state)
    entry = out["tool_results"][0]
    assert entry["ok"] is True
    assert entry["tool"] == NO_TOOL_NAME
    assert json.loads(entry["result"])["skipped"] is True
