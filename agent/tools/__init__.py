"""Tool registry — gom theo nhóm thư mục (search, coingecko, calc, timeutil...)."""

from __future__ import annotations

from langchain_core.tools import BaseTool

from agent.tools.calc import get_calc_tools
from agent.tools.coingecko import get_coingecko_tools
from agent.tools.pdf import get_pdf_tools
from agent.tools.search import get_tavily_search_tool
from agent.tools.timeutil import get_timeutil_tools


def get_tools() -> list[BaseTool]:
    """Trả về toàn bộ local tools sẵn sàng bind vào agent/graph."""
    return [
        get_tavily_search_tool(),
        *get_coingecko_tools(),
        *get_calc_tools(),
        *get_timeutil_tools(),
        *get_pdf_tools(),
    ]


__all__ = [
    "get_tools",
    "get_tavily_search_tool",
    "get_coingecko_tools",
    "get_calc_tools",
    "get_timeutil_tools",
    "get_pdf_tools",
]
