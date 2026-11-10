"""multi_plan bịa tool_name → execute_plan rematch như single_tool."""

from __future__ import annotations

import json
from unittest.mock import patch

from agent.nodes.execute_plan import execute_plan_node
from agent.nodes.tool_select import ToolPick
from agent.state import PlanStep, initial_state


def test_execute_plan_rematch_hallucinated_names() -> None:
    state = initial_state("Bây giờ VN mấy giờ rồi search giá vàng")
    state["plan"] = [
        PlanStep(
            tool_name="get_current_datetime",
            tool_args={"timezone": "Asia/Ho_Chi_Minh"},
            purpose="Lấy giờ hiện tại VN",
        ),
        PlanStep(
            tool_name="web_search",
            tool_args={"query": "giá vàng SJC"},
            purpose="Tra giá vàng SJC",
        ),
    ]

    picks = [
        ToolPick(
            tool_name="time_now",
            tool_args={"timezone": "Asia/Ho_Chi_Minh"},
            reason="remap",
        ),
        ToolPick(
            tool_name="tavily_search",
            tool_args={"query": "giá vàng SJC hôm nay"},
            reason="remap",
        ),
    ]

    def fake_pick(query: str, messages=None, **_kwargs):  # noqa: ANN001
        assert picks, query
        return picks.pop(0)

    with (
        patch("agent.nodes.execute_plan.pick_single_tool", side_effect=fake_pick),
        patch(
            "agent.nodes.execute_plan.invoke_named_tool",
            side_effect=lambda **kw: {
                "step": kw["step"],
                "tool": kw["tool_name"],
                "args": kw["tool_args"] or {},
                "result": "{}",
                "ok": True,
            },
        ) as invoke_mock,
    ):
        out = execute_plan_node(state)

    assert len(out["tool_results"]) == 2
    assert out["tool_results"][0]["tool"] == "time_now"
    assert out["tool_results"][1]["tool"] == "tavily_search"
    assert invoke_mock.call_count == 2


def test_execute_plan_soft_fail_when_rematch_fails() -> None:
    state = initial_state("x")
    state["plan"] = [
        PlanStep(tool_name="", purpose="làm gì đó"),
    ]

    with patch(
        "agent.nodes.execute_plan.pick_single_tool",
        return_value=ToolPick(tool_name="", reason="fail"),
    ):
        out = execute_plan_node(state)

    entry = out["tool_results"][0]
    assert entry["ok"] is False
    payload = json.loads(entry["result"])
    assert "Unknown tool" in payload["error"]
    assert "Available tools" in payload["error"]
