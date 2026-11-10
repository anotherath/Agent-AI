"""Node gather_review: Jev → LLM; hết budget → ép generate."""

from __future__ import annotations

from typing import Any

from agent.routing import decide_review
from agent.state import (
    DEFAULT_JEV_CONFIDENCE_THRESHOLD,
    DEFAULT_MAX_REVIEW_LOOPS,
    AgentState,
    ReviewDecision,
)
from agent.tools.registry import tool_catalog_text


def gather_review_node(state: AgentState) -> dict[str, Any]:
    review_count = int(state.get("review_count") or 0) + 1
    max_loops = int(state.get("max_review_loops", DEFAULT_MAX_REVIEW_LOOPS))
    threshold = float(
        state.get("jev_confidence_threshold", DEFAULT_JEV_CONFIDENCE_THRESHOLD)
    )

    if review_count > max_loops:
        review = ReviewDecision(
            next="generate",
            reason="max_review_loops exceeded",
            confidence=None,
            decided_by="llm",
        )
        return {
            "review": review,
            "review_count": review_count,
            "after_tool_next": "generate",
        }

    review = decide_review(
        query=state.get("query") or "",
        tool_results=list(state.get("tool_results") or []),
        tool_catalog=tool_catalog_text(),
        threshold=threshold,
    )

    after_tool_next = "gather_review" if review.next == "single_tool" else "generate"
    return {
        "review": review,
        "review_count": review_count,
        "after_tool_next": after_tool_next,
    }
