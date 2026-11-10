"""LLM bịa tool_name → validate/rematch, không KeyError."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch

from agent.nodes.single_tool import single_tool_node
from agent.nodes.tool_invoke import invoke_named_tool
from agent.nodes.tool_select import ToolPick, pick_single_tool
from agent.state import RouteDecision, initial_state
from agent.tools.registry import resolve_tool_name, sanitize_route_decision


def test_resolve_tool_name_exact_only() -> None:
    assert resolve_tool_name("time_now") == "time_now"
    assert resolve_tool_name("get_current_time") is None
    assert resolve_tool_name("") is None
    assert resolve_tool_name(None) is None


def test_sanitize_route_clears_hallucinated_tool_name() -> None:
    decision = RouteDecision(
        route="single_tool",
        tool_name="get_weather_forecast",
        tool_args={"date": "tomorrow"},
        decided_by="llm",
    )
    cleaned = sanitize_route_decision(decision)
    assert cleaned.route == "single_tool"
    assert cleaned.tool_name is None
    assert cleaned.tool_args is None


def test_single_tool_rematch_after_invented_name() -> None:
    state = initial_state("Bây giờ là mấy giờ?")
    state["route"] = RouteDecision(
        route="single_tool",
        tool_name="get_current_time",
        decided_by="llm",
    )

    fake_pick = ToolPick(tool_name="time_now", tool_args={"timezone": "UTC"})

    with (
        patch(
            "agent.nodes.single_tool.pick_single_tool",
            return_value=fake_pick,
        ),
        patch(
            "agent.nodes.single_tool.invoke_named_tool",
            return_value={
                "step": 0,
                "tool": "time_now",
                "args": {"timezone": "UTC"},
                "result": '{"now":{}}',
                "ok": True,
            },
        ) as invoke_mock,
    ):
        out = single_tool_node(state)

    invoke_mock.assert_called_once()
    assert invoke_mock.call_args.kwargs["tool_name"] == "time_now"
    assert out["tool_results"][0]["ok"] is True
    assert out["tool_results"][0]["tool"] == "time_now"


def test_single_tool_soft_fail_when_pick_also_invalid() -> None:
    state = initial_state("mấy giờ?")
    state["route"] = RouteDecision(
        route="single_tool",
        tool_name="get_current_time",
        decided_by="llm",
    )
    fake_pick = ToolPick(tool_name="still_wrong", tool_args={})

    with patch(
        "agent.nodes.single_tool.pick_single_tool",
        return_value=fake_pick,
    ):
        out = single_tool_node(state)

    entry = out["tool_results"][0]
    assert entry["ok"] is False
    assert entry["tool"] == "still_wrong"
    payload = json.loads(entry["result"])
    assert "Unknown tool" in payload["error"]
    assert "Available tools" in payload["error"]


def test_invoke_named_tool_soft_fail_unknown() -> None:
    entry = invoke_named_tool(
        tool_name="get_current_time",
        tool_args={},
        query="now?",
        tool_results=[],
        step=0,
    )
    assert entry["ok"] is False
    assert "Unknown tool" in json.loads(entry["result"])["error"]


def test_pick_single_tool_handles_none_structured_output() -> None:
    fake_llm = type(
        "Fake",
        (),
        {"invoke": staticmethod(lambda _msgs: None)},
    )()

    with patch(
        "agent.nodes.tool_select.get_chat_model",
        return_value=type(
            "M",
            (),
            {"with_structured_output": staticmethod(lambda _schema: fake_llm)},
        )(),
    ):
        picked = pick_single_tool("mấy giờ?")

    assert picked.tool_name == ""
    assert picked.reason == "structured_output_none"


def test_pick_single_tool_retries_after_invalid_name() -> None:
    calls: list[Any] = []

    class FakeLLM:
        def invoke(self, msgs: list) -> ToolPick:
            calls.append(msgs)
            if len(calls) == 1:
                return ToolPick(tool_name="get_weather_forecast", tool_args={})
            return ToolPick(
                tool_name="tavily_search",
                tool_args={"query": "weather"},
                reason="retry",
            )

    with patch(
        "agent.nodes.tool_select.get_chat_model",
        return_value=type(
            "M",
            (),
            {"with_structured_output": staticmethod(lambda _schema: FakeLLM())},
        )(),
    ):
        picked = pick_single_tool("dự báo thời tiết ngày mai")

    assert len(calls) == 2
    assert picked.tool_name == "tavily_search"
    assert "không phải tool hợp lệ" in calls[1][1]["content"]
