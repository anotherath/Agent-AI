"""State dùng chung của graph + schema quyết định.

Mỗi node đọc/ghi một phần AgentState; LangGraph merge lại giữa các bước.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from agent.config import (
    DEFAULT_JEV_CONFIDENCE_THRESHOLD,
    DEFAULT_MAX_REVIEW_LOOPS,
    get_jev_confidence_threshold,
    get_max_review_loops,
)

# --- Literals ---

RouteKind = Literal["direct", "single_tool", "multi_plan"]
ReviewNext = Literal["generate", "single_tool", "multi_plan"]
DecidedBy = Literal["jev", "llm"]
AfterToolNext = Literal["generate", "gather_review"]


# --- Schema quyết định / plan / tool ---


class PlanStep(BaseModel):
    """Một bước trong multi_plan. tool_args có thể là literal hoặc `$stepN.path`."""

    tool_name: str
    tool_args: dict[str, Any] = Field(default_factory=dict)
    purpose: str = ""


class RouteDecision(BaseModel):
    """Output orchestrator → chọn nhánh."""

    route: RouteKind
    need_retrieve: bool = False  # reserved (retrieve chưa gắn graph)
    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None
    plan: list[PlanStep] | None = None  # plan thô optional
    reason: str = ""
    confidence: float | None = None  # từ Jev; LLM → null
    decided_by: DecidedBy = "llm"


class ReviewDecision(BaseModel):
    """Output gather_review → bước tiếp theo sau execute."""

    next: ReviewNext
    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None
    reason: str = ""
    confidence: float | None = None
    decided_by: DecidedBy = "llm"


class ToolResult(TypedDict, total=False):
    """Một lần gọi tool (append vào tool_results)."""

    step: int
    tool: str
    args: dict[str, Any]
    result: Any
    ok: bool


# --- State graph ---


class AgentState(TypedDict, total=False):
    """Túi dữ liệu xuyên suốt graph."""

    # Input
    query: str
    user_id: str
    messages: list

    # Quyết định
    route: RouteDecision | None
    review: ReviewDecision | None
    plan: list[PlanStep]
    step_index: int

    # RAG (chưa dùng trong graph hiện tại)
    documents_candidates: list
    documents: list
    retrieve_k: int
    rerank_top_n: int

    # Tools
    tool_results: list[ToolResult]
    after_tool_next: AfterToolNext  # single_tool xong → generate | gather_review

    # Budget / threshold
    review_count: int
    max_review_loops: int
    jev_confidence_threshold: float

    # Output
    answer: str


def initial_state(
    query: str,
    *,
    user_id: str = "",
    messages: list | None = None,
    max_review_loops: int | None = None,
    jev_confidence_threshold: float | None = None,
) -> AgentState:
    """State mặc định trước START.

    max_review_loops / jev_confidence_threshold: None → đọc từ env
    (MAX_REVIEW_LOOPS, JEV_CONFIDENCE_THRESHOLD).
    """
    return {
        "query": query,
        "user_id": user_id,
        "messages": messages or [],
        "route": None,
        "review": None,
        "plan": [],
        "step_index": 0,
        "documents_candidates": [],
        "documents": [],
        "retrieve_k": 20,
        "rerank_top_n": 5,
        "tool_results": [],
        "after_tool_next": "generate",
        "review_count": 0,
        "max_review_loops": (
            get_max_review_loops() if max_review_loops is None else max_review_loops
        ),
        "jev_confidence_threshold": (
            get_jev_confidence_threshold()
            if jev_confidence_threshold is None
            else jev_confidence_threshold
        ),
        "answer": "",
    }


__all__ = [
    "AgentState",
    "PlanStep",
    "RouteDecision",
    "ReviewDecision",
    "ToolResult",
    "RouteKind",
    "ReviewNext",
    "DecidedBy",
    "AfterToolNext",
    "DEFAULT_MAX_REVIEW_LOOPS",
    "DEFAULT_JEV_CONFIDENCE_THRESHOLD",
    "initial_state",
]
