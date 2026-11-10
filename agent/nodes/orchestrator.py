"""Node orchestrator: Jev → LLM → RouteDecision."""

from __future__ import annotations

from typing import Any

from agent.routing import decide_route
from agent.state import (
    DEFAULT_JEV_CONFIDENCE_THRESHOLD,
    AgentState,
)
from agent.tools.registry import tool_catalog_text


def orchestrator_node(state: AgentState) -> dict[str, Any]:
    query = state.get("query") or ""
    threshold = float(
        state.get("jev_confidence_threshold", DEFAULT_JEV_CONFIDENCE_THRESHOLD)
    )
    route = decide_route(
        query=query,
        tool_catalog=tool_catalog_text(),
        messages=state.get("messages"),
        threshold=threshold,
    )
    after_tool_next = "generate"
    return {
        "route": route,
        "review": None,
        "after_tool_next": after_tool_next,
    }
