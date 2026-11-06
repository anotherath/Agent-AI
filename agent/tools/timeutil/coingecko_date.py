"""Tool: format ngày cho CoinGecko history."""

from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from agent.tools.timeutil.core import format_payload, parse_datetime, to_tool_result
from agent.tools.timeutil.descriptions import TO_COINGECKO_DATE


class CoinGeckoDateInput(BaseModel):
    datetime_str: str = Field(
        description="Ngày/thời gian: ISO, yyyy-mm-dd, hoặc dd-mm-yyyy"
    )
    timezone: str = Field(default="UTC")


def time_to_coingecko_date(datetime_str: str, timezone: str = "UTC") -> str:
    """Đổi sang dd-mm-yyyy cho coingecko_history."""
    try:
        dt = parse_datetime(datetime_str, default_tz=timezone)
        payload = format_payload(dt)
        return to_tool_result(
            {
                "input": datetime_str,
                "coingecko_date": payload["coingecko_date"],
                "detail": payload,
            }
        )
    except Exception as exc:  # noqa: BLE001
        return to_tool_result({"error": str(exc), "input": datetime_str})


def get_time_to_coingecko_date_tool() -> StructuredTool:
    return StructuredTool.from_function(
        name="time_to_coingecko_date",
        description=TO_COINGECKO_DATE,
        func=time_to_coingecko_date,
        args_schema=CoinGeckoDateInput,
    )
