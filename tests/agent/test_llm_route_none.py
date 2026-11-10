"""llm_route: structured output None không được crash Pydantic."""

from __future__ import annotations

from unittest.mock import patch

from agent.routing.llm_fallback import llm_route
from agent.state import RouteDecision


def test_llm_route_retries_then_fallback_on_none() -> None:
    class FakeLLM:
        def __init__(self) -> None:
            self.calls = 0

        def invoke(self, _msgs: list) -> None:
            self.calls += 1
            return None

    fake = FakeLLM()
    with patch(
        "agent.routing.llm_fallback.get_chat_model",
        return_value=type(
            "M",
            (),
            {"with_structured_output": staticmethod(lambda _schema: fake)},
        )(),
    ):
        decision = llm_route(query="tính gì đó", tool_catalog="- calc_solve: ...")

    assert fake.calls == 2
    assert isinstance(decision, RouteDecision)
    assert decision.route == "multi_plan"
    assert "structured_output_none" in decision.reason


def test_llm_route_ok_on_second_try() -> None:
    class FakeLLM:
        def __init__(self) -> None:
            self.calls = 0

        def invoke(self, _msgs: list) -> RouteDecision | None:
            self.calls += 1
            if self.calls == 1:
                return None
            return RouteDecision(route="multi_plan", reason="ok", decided_by="llm")

    fake = FakeLLM()
    with patch(
        "agent.routing.llm_fallback.get_chat_model",
        return_value=type(
            "M",
            (),
            {"with_structured_output": staticmethod(lambda _schema: fake)},
        )(),
    ):
        decision = llm_route(query="x", tool_catalog="- t")

    assert fake.calls == 2
    assert decision.route == "multi_plan"
    assert decision.reason == "ok"
