"""Tool: time_convert — đổi timezone."""

from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from agent.tools.timeutil.core import (
    format_payload,
    get_tz,
    parse_datetime,
    to_tool_result,
)
from agent.tools.timeutil.descriptions import (
    TIME_CONVERT,
    TIME_CONVERT_DATETIME_STR,
    TIME_CONVERT_FROM_TIMEZONE,
    TIME_CONVERT_TO_TIMEZONE,
)


class ConvertInput(BaseModel):
    datetime_str: str = Field(description=TIME_CONVERT_DATETIME_STR)
    from_timezone: str = Field(default="UTC", description=TIME_CONVERT_FROM_TIMEZONE)
    to_timezone: str = Field(
        default="Asia/Ho_Chi_Minh",
        description=TIME_CONVERT_TO_TIMEZONE,
    )


def time_convert(
    datetime_str: str,
    from_timezone: str = "UTC",
    to_timezone: str = "Asia/Ho_Chi_Minh",
) -> str:
    """Convert datetime giữa các timezone."""
    try:
        src = parse_datetime(datetime_str, default_tz=from_timezone)
        dst = src.astimezone(get_tz(to_timezone))
        return to_tool_result(
            {
                "input": datetime_str,
                "from": format_payload(src),
                "to": format_payload(dst),
            }
        )
    except Exception as exc:  # noqa: BLE001
        return to_tool_result({"error": str(exc), "input": datetime_str})


def get_time_convert_tool() -> StructuredTool:
    return StructuredTool.from_function(
        name="time_convert",
        description=TIME_CONVERT,
        func=time_convert,
        args_schema=ConvertInput,
    )
