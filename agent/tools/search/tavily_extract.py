"""Tavily Extract — đọc nội dung trang theo URL."""

from __future__ import annotations

from typing import Any, Literal

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from tavily import TavilyClient

from agent.tools.search.client import require_api_key, to_tool_result
from agent.tools.search.descriptions import (
    TAVILY_EXTRACT,
    TAVILY_EXTRACT_EXTRACT_DEPTH,
    TAVILY_EXTRACT_FORMAT,
    TAVILY_EXTRACT_URL,
)

ExtractDepth = Literal["basic", "advanced"]
ContentFormat = Literal["markdown", "text"]


class ExtractInput(BaseModel):
    url: str = Field(description=TAVILY_EXTRACT_URL)
    extract_depth: ExtractDepth = Field(
        default="basic",
        description=TAVILY_EXTRACT_EXTRACT_DEPTH,
    )
    format: ContentFormat = Field(
        default="markdown",
        description=TAVILY_EXTRACT_FORMAT,
    )


def tavily_extract(
    url: str,
    extract_depth: ExtractDepth = "basic",
    format: ContentFormat = "markdown",
) -> str:
    """Gọi Tavily Extract cho một URL; trả JSON string."""
    try:
        client = TavilyClient(api_key=require_api_key())
        raw = client.extract(
            urls=url.strip(),
            extract_depth=extract_depth,
            format=format,
        )
        results = raw.get("results") or []
        failed = raw.get("failed_results") or []
        if not results and failed:
            return to_tool_result(
                {
                    "error": "Extract thất bại",
                    "url": url,
                    "failed_results": failed,
                }
            )
        item = results[0] if len(results) == 1 else None
        payload: dict[str, Any] = {
            "url": url,
            "extract_depth": extract_depth,
            "format": format,
            "results": results,
            "failed_results": failed,
        }
        if item is not None:
            payload["content"] = item.get("raw_content") or item.get("content") or ""
            payload["title"] = item.get("title")
        return to_tool_result(payload)
    except ValueError as exc:
        return to_tool_result({"error": str(exc), "url": url})
    except Exception as exc:  # noqa: BLE001
        return to_tool_result({"error": str(exc), "url": url})


def get_tavily_extract_tool() -> StructuredTool:
    require_api_key()
    return StructuredTool.from_function(
        name="tavily_extract",
        description=TAVILY_EXTRACT,
        func=tavily_extract,
        args_schema=ExtractInput,
    )
