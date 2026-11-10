"""Tool: time_shift — cộng/trừ khoảng thời gian."""

from __future__ import annotations

from datetime import datetime, timedelta

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from agent.tools.timeutil.core import (
    format_payload,
    get_tz,
    parse_datetime,
    to_tool_result,
)
from agent.tools.timeutil.descriptions import (
    TIME_SHIFT,
    TIME_SHIFT_DATETIME_STR,
    TIME_SHIFT_DAYS,
    TIME_SHIFT_HOURS,
    TIME_SHIFT_MINUTES,
    TIME_SHIFT_TIMEZONE,
)


class ShiftInput(BaseModel):
    datetime_str: str = Field(default="now", description=TIME_SHIFT_DATETIME_STR)
    days: int = Field(default=0, description=TIME_SHIFT_DAYS)
    hours: int = Field(default=0, description=TIME_SHIFT_HOURS)
    minutes: int = Field(default=0, description=TIME_SHIFT_MINUTES)
    timezone: str = Field(default="UTC", description=TIME_SHIFT_TIMEZONE)


def time_shift(
    datetime_str: str = "now",
    days: int = 0,
    hours: int = 0,
    minutes: int = 0,
    timezone: str = "UTC",
) -> str:
    """Shift thời gian theo days/hours/minutes."""
    try:
        if datetime_str.strip().lower() == "now":
            base = datetime.now(tz=get_tz(timezone))
        else:
            base = parse_datetime(datetime_str, default_tz=timezone)

        delta = timedelta(days=days, hours=hours, minutes=minutes)
        result = base + delta
        return to_tool_result(
            {
                "base": format_payload(base),
                "delta": {"days": days, "hours": hours, "minutes": minutes},
                "result": format_payload(result),
            }
        )
    except Exception as exc:  # noqa: BLE001
        return to_tool_result({"error": str(exc), "datetime_str": datetime_str})


def get_time_shift_tool() -> StructuredTool:
    return StructuredTool.from_function(
        name="time_shift",
        description=TIME_SHIFT,
        func=time_shift,
        args_schema=ShiftInput,
    )
