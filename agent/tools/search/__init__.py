"""Web search / extract tools (Tavily)."""

from __future__ import annotations

from langchain_core.tools import BaseTool

from agent.tools.search.tavily_extract import get_tavily_extract_tool
from agent.tools.search.tavily_search import get_tavily_search_tool


def get_search_tools() -> list[BaseTool]:
    return [
        get_tavily_search_tool(),
        get_tavily_extract_tool(),
    ]


__all__ = [
    "get_search_tools",
    "get_tavily_search_tool",
    "get_tavily_extract_tool",
]
