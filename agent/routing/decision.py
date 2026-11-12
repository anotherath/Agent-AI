"""Cascade: Jev (nếu conf đủ) → LLM structured fallback."""

from __future__ import annotations

import json
from typing import Any

from agent.prompts.gather_review import (
    GATHER_REVIEW_CRITERIA,
    GATHER_REVIEW_INSTRUCTIONS,
)
from agent.prompts.orchestrator import (
    ORCHESTRATOR_CRITERIA,
    ORCHESTRATOR_INSTRUCTIONS,
)
from agent.routing.jev_client import classify_choice
from agent.routing.llm_fallback import llm_review, llm_route
from agent.state import (
    DEFAULT_JEV_CONFIDENCE_THRESHOLD,
    ReviewDecision,
    RouteDecision,
    RouteKind,
    ReviewNext,
)

_ROUTE_OPTIONS = frozenset(ORCHESTRATOR_CRITERIA)
_REVIEW_OPTIONS = frozenset(GATHER_REVIEW_CRITERIA)


def decide_route(
    *,
    query: str,
    tool_catalog: str,
    messages: list | None = None,
    threshold: float = DEFAULT_JEV_CONFIDENCE_THRESHOLD,
) -> RouteDecision:
    state: dict[str, Any] = {"query": query}
    if messages:
        state["messages"] = messages

    jev = classify_choice(
        state=state,
        question_id="route",
        instructions=ORCHESTRATOR_INSTRUCTIONS,
        criteria=ORCHESTRATOR_CRITERIA,
    )
    if jev is not None and jev.confidence >= threshold and jev.choice in _ROUTE_OPTIONS:
        return RouteDecision(
            route=jev.choice,  # type: ignore[arg-type]
            reason="jev",
            confidence=jev.confidence,
            decided_by="jev",
        )

    return llm_route(query=query, tool_catalog=tool_catalog, messages=messages)


def decide_review(
    *,
    query: str,
    tool_results: list,
    tool_catalog: str,
    threshold: float = DEFAULT_JEV_CONFIDENCE_THRESHOLD,
) -> ReviewDecision:
    state = {
        "query": query,
        "tool_results": json.dumps(tool_results, ensure_ascii=False, default=str),
    }
    jev = classify_choice(
        state=state,
        question_id="review",
        instructions=GATHER_REVIEW_INSTRUCTIONS.format(tool_catalog=tool_catalog),
        criteria=GATHER_REVIEW_CRITERIA,
    )
    if jev is not None and jev.confidence >= threshold and jev.choice in _REVIEW_OPTIONS:
        return ReviewDecision(
            next=jev.choice,  # type: ignore[arg-type]
            reason="jev",
            confidence=jev.confidence,
            decided_by="jev",
        )

    return llm_review(
        query=query,
        tool_results=tool_results,
        tool_catalog=tool_catalog,
    )


def coerce_route(value: str) -> RouteKind:
    if value not in _ROUTE_OPTIONS:
        raise ValueError(f"Invalid route: {value}")
    return value  # type: ignore[return-value]


def coerce_review_next(value: str) -> ReviewNext:
    if value not in _REVIEW_OPTIONS:
        raise ValueError(f"Invalid review next: {value}")
    return value  # type: ignore[return-value]


__all__ = ["decide_route", "decide_review", "coerce_route", "coerce_review_next"]
