"""Tavily web search tool."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.tools import BaseTool

load_dotenv()

DEFAULT_MAX_RESULTS = 5

TAVILY_SEARCH_DESCRIPTION = (
    "Tìm kiếm web bằng Tavily Search API để lấy thông tin mới nhất từ internet. "
    "Trả về danh sách kết quả gồm tiêu đề, URL và nội dung tóm tắt, "
    "trích xuất của từng trang."
)


def get_tavily_search_tool(
    *,
    max_results: int = DEFAULT_MAX_RESULTS,
    search_depth: str = "basic",
    include_answer: bool = True,
) -> BaseTool:
    if not os.getenv("TAVILY_API_KEY"):
        raise ValueError(
            "Missing TAVILY_API_KEY. Set it in the environment or .env file."
        )

    return TavilySearchResults(
        name="tavily_search",
        description=TAVILY_SEARCH_DESCRIPTION,
        max_results=max_results,
        search_depth=search_depth,
        include_answer=include_answer,
    )
