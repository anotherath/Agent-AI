"""Khung LangGraph: lắp node + edge. Logic chi tiết nằm ở nodes/ và routing/.

Chưa gắn: retrieve / guard.
"""

from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from agent.nodes import (
    gather_review_node,
    generate_node,
    orchestrator_node,
    plan_execution_node,
    planner_node,
    tool_execution_node,
    tool_select_node,
)
from agent.state import AgentState, initial_state


# --- Conditional edges: đọc state → tên node tiếp theo ---


def _route_after_orchestrator(
    state: AgentState,
) -> Literal["generate", "tool_select", "planner"]:
    """direct → generate | single_tool → tool_select | multi_plan → planner."""
    route = state.get("route")
    if route is None:
        return "generate"
    if route.route == "single_tool":
        return "tool_select"
    if route.route == "multi_plan":
        return "planner"
    return "generate"  # direct


def _route_after_tool_execution(
    state: AgentState,
) -> Literal["generate", "gather_review"]:
    """Từ orchestrator → generate; từ gather_review (thiếu 1 tool) → quay lại review."""
    nxt = state.get("after_tool_next") or "generate"
    if nxt == "gather_review":
        return "gather_review"
    return "generate"


def _route_after_review(
    state: AgentState,
) -> Literal["generate", "tool_select", "planner"]:
    """đủ → generate | thiếu 1 → tool_select | thiếu nhiều → planner."""
    review = state.get("review")
    if review is None:
        return "generate"
    if review.next == "single_tool":
        return "tool_select"
    if review.next == "multi_plan":
        return "planner"
    return "generate"


# --- Build graph ---


def build_graph() -> StateGraph:
    """Đăng ký node + nối cạnh (chưa compile)."""
    graph = StateGraph(AgentState)

    # Nodes
    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("tool_select", tool_select_node)
    graph.add_node("tool_execution", tool_execution_node)
    graph.add_node("planner", planner_node)
    graph.add_node("plan_execution", plan_execution_node)
    graph.add_node("gather_review", gather_review_node)
    graph.add_node("generate", generate_node)

    # Edges
    graph.add_edge(START, "orchestrator")
    graph.add_conditional_edges(
        "orchestrator",
        _route_after_orchestrator,
        {
            "generate": "generate",
            "tool_select": "tool_select",
            "planner": "planner",
        },
    )
    graph.add_edge("tool_select", "tool_execution")
    graph.add_conditional_edges(
        "tool_execution",
        _route_after_tool_execution,
        {
            "generate": "generate",
            "gather_review": "gather_review",
        },
    )
    graph.add_edge("planner", "plan_execution")
    graph.add_edge("plan_execution", "gather_review")
    graph.add_conditional_edges(
        "gather_review",
        _route_after_review,
        {
            "generate": "generate",
            "tool_select": "tool_select",
            "planner": "planner",
        },
    )
    graph.add_edge("generate", END)
    return graph


@lru_cache(maxsize=1)
def get_compiled_graph():
    """Graph đã compile (cache 1 instance)."""
    return build_graph().compile()


def clear_graph_cache() -> None:
    get_compiled_graph.cache_clear()


def run_agent(
    query: str,
    *,
    user_id: str = "",
    messages: list | None = None,
    model: str | None = None,
    **kwargs: Any,
) -> AgentState:
    """Invoke → state cuối (đọc `answer`). Dùng ainvoke vì generate là async."""
    from agent.models import llm_model_scope

    graph = get_compiled_graph()
    state = initial_state(
        query, user_id=user_id, messages=messages, model=model, **kwargs
    )
    with llm_model_scope(model):
        return asyncio.run(graph.ainvoke(state))


__all__ = [
    "build_graph",
    "get_compiled_graph",
    "clear_graph_cache",
    "run_agent",
    "initial_state",
]
