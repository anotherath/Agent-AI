"""Tool: thời gian hiện tại."""

from __future__ import annotations

from datetime import datetime

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from agent.tools.timeutil.core import format_payload, get_tz, to_tool_result
from agent.tools.timeutil.descriptions import NOW


class NowInput(BaseModel):
    timezone: str = Field(
        default="UTC",
        description="IANA timezone, ví dụ: UTC, Asia/Ho_Chi_Minh",
    )


def time_now(timezone: str = "UTC") -> str:
    """Lấy now theo timezone."""
    try:
        tz = get_tz(timezone)
        now = datetime.now(tz=tz)
        return to_tool_result({"now": format_payload(now)})
    except Exception as exc:  # noqa: BLE001
        return to_tool_result({"error": str(exc)})


def get_time_now_tool() -> StructuredTool:
    return StructuredTool.from_function(
        name="time_now",
        description=NOW,
        func=time_now,
        args_schema=NowInput,
    )
