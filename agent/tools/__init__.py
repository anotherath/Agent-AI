"""Tool registry — gom theo nhóm thư mục (search, calc, timeutil, document...)."""

from __future__ import annotations

from langchain_core.tools import BaseTool

from agent.tools.calc import get_calc_tools
from agent.tools.document import get_document_tools
from agent.tools.search import get_search_tools, get_tavily_search_tool
from agent.tools.timeutil import get_timeutil_tools


def get_tools() -> list[BaseTool]:
    """Trả về toàn bộ local tools sẵn sàng bind vào agent/graph.

    document tools tạm thời chưa đăng ký catalog (get_document_tools vẫn dùng được riêng).
    """
    return [
        *get_search_tools(),
        *get_calc_tools(),
        *get_timeutil_tools(),
        # *get_document_tools(),
    ]


__all__ = [
    "get_tools",
    "get_search_tools",
    "get_tavily_search_tool",
    "get_calc_tools",
    "get_timeutil_tools",
    "get_document_tools",
]
