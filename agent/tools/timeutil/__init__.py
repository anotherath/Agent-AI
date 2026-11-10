"""Datetime / timezone tools."""

from __future__ import annotations

from langchain_core.tools import BaseTool

from agent.tools.timeutil.time_convert import get_time_convert_tool
from agent.tools.timeutil.time_now import get_time_now_tool
from agent.tools.timeutil.time_shift import get_time_shift_tool


def get_timeutil_tools() -> list[BaseTool]:
    return [
        get_time_now_tool(),
        get_time_convert_tool(),
        get_time_shift_tool(),
    ]


__all__ = ["get_timeutil_tools"]
