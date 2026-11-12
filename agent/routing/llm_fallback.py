"""LLM structured fallback cho route / review (cùng schema Pydantic)."""

from __future__ import annotations

from typing import Any

from agent.models import get_chat_model
from agent.prompts.gather_review import (
    GATHER_REVIEW_LLM_SYSTEM,
    GATHER_REVIEW_LLM_USER,
)
from agent.prompts.orchestrator import ORCHESTRATOR_LLM_SYSTEM
from agent.state import ReviewDecision, RouteDecision
from agent.tools.registry import sanitize_review_decision


def _coerce_route(result: Any) -> RouteDecision:
    if isinstance(result, RouteDecision):
        decision = result
    elif result is None:
        raise ValueError("structured_output_none")
    else:
        # Extra fields (tool_name, …) bị Pydantic bỏ — schema orchestrator chỉ còn nhánh.
        decision = RouteDecision.model_validate(result)
    decision.decided_by = "llm"
    decision.confidence = None
    return decision


def _coerce_review(result: Any) -> ReviewDecision:
    if isinstance(result, ReviewDecision):
        decision = result
    elif result is None:
        raise ValueError("structured_output_none")
    else:
        decision = ReviewDecision.model_validate(result)
    decision.decided_by = "llm"
    decision.confidence = None
    return sanitize_review_decision(decision)


def llm_route(
    *,
    query: str,
    tool_catalog: str,
    messages: list | None = None,
) -> RouteDecision:
    llm = get_chat_model().with_structured_output(RouteDecision)
    system = ORCHESTRATOR_LLM_SYSTEM.format(tool_catalog=tool_catalog)
    human = f"Query: {query}"
    if messages:
        human += f"\nMessages: {messages!r}"
    chat = [
        {"role": "system", "content": system},
        {"role": "user", "content": human},
    ]
    result = llm.invoke(chat)
    try:
        return _coerce_route(result)
    except Exception:
        # DeepSeek/proxy đôi khi trả content rỗng → structured output = None.
        retry = llm.invoke(
            [
                *chat,
                {
                    "role": "user",
                    "content": (
                        "Lần trước không trả RouteDecision hợp lệ. "
                        "Bắt buộc điền schema RouteDecision (route + reason)."
                    ),
                },
            ]
        )
        try:
            return _coerce_route(retry)
        except Exception:
            # Không để crash UI — mặc định multi_plan để tool_select/plan tiếp tục.
            return RouteDecision(
                route="multi_plan",
                reason="structured_output_none: fallback multi_plan",
                decided_by="llm",
                confidence=None,
            )


def llm_review(
    *,
    query: str,
    tool_results: list,
    tool_catalog: str,
) -> ReviewDecision:
    llm = get_chat_model().with_structured_output(ReviewDecision)
    system = GATHER_REVIEW_LLM_SYSTEM.format(tool_catalog=tool_catalog)
    user = GATHER_REVIEW_LLM_USER.format(
        query=query,
        tool_results=tool_results,
    )
    chat = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    result = llm.invoke(chat)
    try:
        return _coerce_review(result)
    except Exception:
        retry = llm.invoke(
            [
                *chat,
                {
                    "role": "user",
                    "content": (
                        "Lần trước không trả ReviewDecision hợp lệ. "
                        "Bắt buộc điền schema ReviewDecision (next + reason)."
                    ),
                },
            ]
        )
        try:
            return _coerce_review(retry)
        except Exception:
            return sanitize_review_decision(
                ReviewDecision(
                    next="generate",
                    reason="structured_output_none: fallback generate",
                    decided_by="llm",
                    confidence=None,
                )
            )


__all__ = ["llm_route", "llm_review"]
