"""Unit tests graph wiring + cascade routing (mock Jev/LLM)."""

from __future__ import annotations

from unittest.mock import patch

from agent.graph import build_graph, get_compiled_graph, clear_graph_cache
from agent.state import ReviewDecision, RouteDecision, initial_state


def test_build_graph_has_expected_nodes():
    g = build_graph()
    names = set(g.nodes)
    for node in (
        "orchestrator",
        "single_tool",
        "multi_plan",
        "execute_plan",
        "gather_review",
        "generate",
    ):
        assert node in names
    assert "retrieve" not in names
    assert "input_guard" not in names
    assert "output_guard" not in names


def test_orchestrator_direct_to_generate():
    clear_graph_cache()
    decision = RouteDecision(
        route="direct",
        reason="chào",
        decided_by="llm",
    )

    def fake_generate(state):
        return {"answer": "Xin chào!"}

    with (
        patch("agent.nodes.orchestrator.decide_route", return_value=decision),
        patch("agent.graph.generate_node", new=fake_generate),
    ):
        clear_graph_cache()
        # compile mới để bind mock node
        from agent.graph import build_graph

        graph = build_graph().compile()
        out = graph.invoke(initial_state("Chào bạn"))
    assert out["answer"] == "Xin chào!"
    assert out["route"].route == "direct"


def test_gather_review_budget_forces_generate():
    from agent.nodes.gather_review import gather_review_node

    state = initial_state("q", max_review_loops=1)
    state["review_count"] = 1
    state["tool_results"] = [{"step": 0, "tool": "time_now", "ok": True}]

    with patch("agent.nodes.gather_review.decide_review") as mocked:
        out = gather_review_node(state)
        mocked.assert_not_called()
    assert out["review"].next == "generate"
    assert "max_review_loops" in out["review"].reason


def test_decide_route_jev_high_conf():
    from agent.routing.decide import decide_route
    from agent.routing.jev_client import JevChoiceResult

    jev = JevChoiceResult(
        choice="direct",
        confidence=0.95,
        probabilities={"direct": 0.95, "single_tool": 0.03, "multi_plan": 0.02},
    )
    with (
        patch("agent.routing.decide.classify_choice", return_value=jev),
        patch("agent.routing.decide.llm_route") as llm,
    ):
        decision = decide_route(query="hi", tool_catalog="- time_now: now")
        llm.assert_not_called()
    assert decision.route == "direct"
    assert decision.decided_by == "jev"


def test_decide_route_low_conf_falls_back_llm():
    from agent.routing.decide import decide_route
    from agent.routing.jev_client import JevChoiceResult

    jev = JevChoiceResult(
        choice="direct",
        confidence=0.2,
        probabilities={"direct": 0.4, "single_tool": 0.3, "multi_plan": 0.3},
    )
    fallback = RouteDecision(route="single_tool", tool_name="time_now", decided_by="llm")
    with (
        patch("agent.routing.decide.classify_choice", return_value=jev),
        patch("agent.routing.decide.llm_route", return_value=fallback) as llm,
    ):
        decision = decide_route(query="mấy giờ", tool_catalog="- time_now: now")
        llm.assert_called_once()
    assert decision.route == "single_tool"
    assert decision.decided_by == "llm"


def test_knobs_from_env(monkeypatch):
    from agent import config
    from agent.state import initial_state

    monkeypatch.setenv("MAX_REVIEW_LOOPS", "3")
    monkeypatch.setenv("JEV_CONFIDENCE_THRESHOLD", "0.8")
    assert config.get_max_review_loops() == 3
    assert config.get_jev_confidence_threshold() == 0.8
    state = initial_state("hi")
    assert state["max_review_loops"] == 3
    assert state["jev_confidence_threshold"] == 0.8


def test_no_typesafe_key_falls_back_llm(monkeypatch):
    from agent.routing import jev_client
    from agent.routing.decide import decide_route

    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    assert jev_client.jev_available() is False
    assert jev_client.classify_choice(
        state={"query": "hi"},
        question_id="route",
        instructions="x",
        criteria={"direct": "a"},
    ) is None

    fallback = RouteDecision(route="direct", decided_by="llm")
    with patch("agent.routing.decide.llm_route", return_value=fallback) as llm:
        decision = decide_route(query="hi", tool_catalog="- time_now: now")
        llm.assert_called_once()
    assert decision.decided_by == "llm"
