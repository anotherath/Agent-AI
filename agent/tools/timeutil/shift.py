"""Tool: cộng/trừ khoảng thời gian."""

from __future__ import annotations

from datetime import timedelta

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from agent.tools.timeutil.core import format_payload, parse_datetime, to_tool_result
from agent.tools.timeutil.descriptions import SHIFT


class ShiftInput(BaseModel):
    datetime_str: str = Field(
        default="now",
        description="Mốc gốc: 'now' hoặc ISO / yyyy-mm-dd / dd-mm-yyyy",
    )
    days: int = Field(default=0)
    hours: int = Field(default=0)
    minutes: int = Field(default=0)
    timezone: str = Field(default="UTC", description="Timezone khi parse naive/'now'")


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
            from datetime import datetime

            from agent.tools.timeutil.core import get_tz

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
        description=SHIFT,
        func=time_shift,
        args_schema=ShiftInput,
    )
