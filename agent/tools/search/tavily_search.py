"""Tavily Search — tìm kiếm web theo query."""

from __future__ import annotations

from typing import Any, Literal

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from tavily import TavilyClient

from agent.tools.search.client import (
    DEFAULT_SEARCH_MAX_RESULTS_CAP,
    compact_tavily_search_payload,
    require_api_key,
    to_tool_result,
)
from agent.tools.search.descriptions import (
    TAVILY_SEARCH,
    TAVILY_SEARCH_INCLUDE_ANSWER,
    TAVILY_SEARCH_MAX_RESULTS,
    TAVILY_SEARCH_QUERY,
    TAVILY_SEARCH_SEARCH_DEPTH,
)

DEFAULT_MAX_RESULTS = 5
SearchDepth = Literal["basic", "advanced"]


class SearchInput(BaseModel):
    query: str = Field(description=TAVILY_SEARCH_QUERY)
    max_results: int = Field(
        default=DEFAULT_MAX_RESULTS,
        description=TAVILY_SEARCH_MAX_RESULTS,
    )
    search_depth: SearchDepth = Field(
        default="basic",
        description=TAVILY_SEARCH_SEARCH_DEPTH,
    )
    include_answer: bool = Field(
        default=True,
        description=TAVILY_SEARCH_INCLUDE_ANSWER,
    )


def tavily_search(
    query: str,
    max_results: int = DEFAULT_MAX_RESULTS,
    search_depth: SearchDepth = "basic",
    include_answer: bool = True,
) -> str:
    """Gọi Tavily Search; trả JSON gọn (snippet) cho LLM."""
    try:
        capped = max(1, min(int(max_results), DEFAULT_SEARCH_MAX_RESULTS_CAP))
        client = TavilyClient(api_key=require_api_key())
        raw: dict[str, Any] = client.search(
            query=query.strip(),
            max_results=capped,
            search_depth=search_depth,
            include_answer=include_answer,
        )
        payload = compact_tavily_search_payload(
            query=query,
            results=raw.get("results") or [],
            answer=raw.get("answer") if "answer" in raw else None,
        )
        return to_tool_result(payload)
    except ValueError as exc:
        return to_tool_result({"error": str(exc), "query": query})
    except Exception as exc:  # noqa: BLE001
        return to_tool_result({"error": str(exc), "query": query})


def get_tavily_search_tool() -> StructuredTool:
    require_api_key()
    return StructuredTool.from_function(
        name="tavily_search",
        description=TAVILY_SEARCH,
        func=tavily_search,
        args_schema=SearchInput,
    )
