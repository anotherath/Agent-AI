"""Datetime / timezone tools."""

from __future__ import annotations

from langchain_core.tools import BaseTool

from agent.tools.timeutil.coingecko_date import get_time_to_coingecko_date_tool
from agent.tools.timeutil.convert import get_time_convert_tool
from agent.tools.timeutil.now import get_time_now_tool
from agent.tools.timeutil.shift import get_time_shift_tool


def get_timeutil_tools() -> list[BaseTool]:
    return [
        get_time_now_tool(),
        get_time_convert_tool(),
        get_time_shift_tool(),
        get_time_to_coingecko_date_tool(),
    ]


__all__ = ["get_timeutil_tools"]
