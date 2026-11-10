"""Khung LangGraph: lắp node + edge. Logic chi tiết nằm ở nodes/ và routing/.

Chưa gắn: retrieve / guard.
"""

from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from agent.nodes import (
    execute_plan_node,
    gather_review_node,
    generate_node,
    multi_plan_node,
    orchestrator_node,
    single_tool_node,
)
from agent.state import AgentState, initial_state


# --- Conditional edges: đọc state → tên node tiếp theo ---


def _route_after_orchestrator(
    state: AgentState,
) -> Literal["generate", "single_tool", "multi_plan"]:
    """direct → generate | single_tool | multi_plan."""
    route = state.get("route")
    if route is None:
        return "generate"
    if route.route == "single_tool":
        return "single_tool"
    if route.route == "multi_plan":
        return "multi_plan"
    return "generate"  # direct


def _route_after_single_tool(
    state: AgentState,
) -> Literal["generate", "gather_review"]:
    """Từ orchestrator → generate; từ gather_review (thiếu 1 tool) → quay lại review."""
    nxt = state.get("after_tool_next") or "generate"
    if nxt == "gather_review":
        return "gather_review"
    return "generate"


def _route_after_review(
    state: AgentState,
) -> Literal["generate", "single_tool", "multi_plan"]:
    """đủ → generate | thiếu 1 → single_tool | thiếu nhiều → multi_plan."""
    review = state.get("review")
    if review is None:
        return "generate"
    if review.next == "single_tool":
        return "single_tool"
    if review.next == "multi_plan":
        return "multi_plan"
    return "generate"


# --- Build graph ---


def build_graph() -> StateGraph:
    """Đăng ký node + nối cạnh (chưa compile)."""
    graph = StateGraph(AgentState)

    # Nodes
    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("single_tool", single_tool_node)
    graph.add_node("multi_plan", multi_plan_node)
    graph.add_node("execute_plan", execute_plan_node)
    graph.add_node("gather_review", gather_review_node)
    graph.add_node("generate", generate_node)

    # Edges
    graph.add_edge(START, "orchestrator")
    graph.add_conditional_edges(
        "orchestrator",
        _route_after_orchestrator,
        {
            "generate": "generate",
            "single_tool": "single_tool",
            "multi_plan": "multi_plan",
        },
    )
    graph.add_conditional_edges(
        "single_tool",
        _route_after_single_tool,
        {
            "generate": "generate",
            "gather_review": "gather_review",
        },
    )
    graph.add_edge("multi_plan", "execute_plan")
    graph.add_edge("execute_plan", "gather_review")
    graph.add_conditional_edges(
        "gather_review",
        _route_after_review,
        {
            "generate": "generate",
            "single_tool": "single_tool",
            "multi_plan": "multi_plan",
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
    **kwargs: Any,
) -> AgentState:
    """Invoke → state cuối (đọc `answer`). Dùng ainvoke vì generate là async."""
    graph = get_compiled_graph()
    state = initial_state(query, user_id=user_id, messages=messages, **kwargs)
    return asyncio.run(graph.ainvoke(state))


__all__ = [
    "build_graph",
    "get_compiled_graph",
    "clear_graph_cache",
    "run_agent",
    "initial_state",
]
