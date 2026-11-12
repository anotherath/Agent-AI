"""plan_execution rematch tên tool + args / placeholder."""

from __future__ import annotations

import json
from unittest.mock import patch

from agent.nodes.plan_execution import plan_execution_node
from agent.state import PlanStep, ToolPick, initial_state


def test_plan_execution_rematch_hallucinated_names() -> None:
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
        patch("agent.nodes.plan_execution.pick_single_tool", side_effect=fake_pick),
        patch(
            "agent.nodes.plan_execution.invoke_named_tool",
            side_effect=lambda **kw: {
                "step": kw["step"],
                "tool": kw["tool_name"],
                "args": kw["tool_args"] or {},
                "result": "{}",
                "ok": True,
            },
        ) as invoke_mock,
    ):
        out = plan_execution_node(state)

    assert len(out["tool_results"]) == 2
    assert out["tool_results"][0]["tool"] == "time_now"
    assert out["tool_results"][1]["tool"] == "tavily_search"
    assert invoke_mock.call_count == 2


def test_plan_execution_soft_fail_when_rematch_fails() -> None:
    state = initial_state("x")
    state["plan"] = [
        PlanStep(tool_name="", purpose="làm gì đó"),
    ]

    with patch(
        "agent.nodes.plan_execution.pick_single_tool",
        return_value=ToolPick(tool_name="", reason="fail"),
    ):
        out = plan_execution_node(state)

    entry = out["tool_results"][0]
    assert entry["ok"] is False
    payload = json.loads(entry["result"])
    assert "Unknown tool" in payload["error"]


def test_plan_execution_rematch_fake_placeholder_args() -> None:
    state = initial_state("giá vàng 17 ngày trước")
    state["plan"] = [
        PlanStep(
            tool_name="tavily_search",
            tool_args={"query": "giá vàng ngày {17 ngày trước}"},
            purpose="Tra giá vàng",
        ),
    ]

    with (
        patch(
            "agent.nodes.plan_execution.rematch_step_args",
            return_value={
                "query": "giá vàng ngày 26-10-2026 SJC",
            },
        ) as rematch_mock,
        patch(
            "agent.nodes.plan_execution.invoke_named_tool",
            side_effect=lambda **kw: {
                "step": kw["step"],
                "tool": kw["tool_name"],
                "args": kw["tool_args"] or {},
                "result": "{}",
                "ok": True,
            },
        ) as invoke_mock,
        patch(
            "agent.nodes.plan_execution.get_planner_max_retries",
            return_value=1,
        ),
    ):
        out = plan_execution_node(state)

    rematch_mock.assert_called_once()
    assert invoke_mock.call_count == 1
    assert out["tool_results"][0]["ok"] is True
    assert "{17" not in json.dumps(invoke_mock.call_args.kwargs["tool_args"])


def test_has_fake_placeholder_double_brace() -> None:
    from agent.nodes.util.step_rematch import has_fake_placeholder

    assert has_fake_placeholder({"query": "giá {{today_date}}"})
    assert has_fake_placeholder({"a": "{{today_sjc_buy}}", "b": "{{past_sjc_buy}}"})
    assert has_fake_placeholder({"query": "ngày {17 ngày trước}"})
    assert not has_fake_placeholder(
        {"query": "giá vàng ngày $step0.now.date_dmy"}
    )
    assert not has_fake_placeholder({"timezone": "Asia/Ho_Chi_Minh"})


def test_plan_execution_rematch_missing_required_args() -> None:
    state = initial_state("tính % đổi")
    state["plan"] = [
        PlanStep(
            tool_name="calc_percent_change",
            tool_args={},
            purpose="Tính phần trăm thay đổi",
        ),
    ]

    with (
        patch(
            "agent.nodes.plan_execution.rematch_step_args",
            return_value={"old": 100.0, "new": 120.0},
        ) as rematch_mock,
        patch(
            "agent.nodes.plan_execution.invoke_named_tool",
            side_effect=lambda **kw: {
                "step": kw["step"],
                "tool": kw["tool_name"],
                "args": kw["tool_args"] or {},
                "result": json.dumps({"percent_change": 20.0}),
                "ok": True,
            },
        ),
        patch(
            "agent.nodes.plan_execution.get_planner_max_retries",
            return_value=1,
        ),
    ):
        out = plan_execution_node(state)

    rematch_mock.assert_called_once()
    assert out["tool_results"][0]["ok"] is True
