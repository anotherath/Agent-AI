"""CoinGecko: snapshot lịch sử theo ngày cụ thể."""

from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from agent.tools.coingecko.client import (
    coingecko_get,
    resolve_coin_id,
    to_tool_result,
)
from agent.tools.coingecko.descriptions import HISTORY


class HistoryInput(BaseModel):
    coin: str = Field(description="Tên, symbol hoặc id coin")
    date: str = Field(description="Ngày theo format dd-mm-yyyy")


def fetch_history(coin: str, date: str) -> str:
    """Gọi /coins/{id}/history."""
    resolved = resolve_coin_id(coin)
    if not resolved or not resolved.get("id"):
        return to_tool_result({"error": f"Không tìm thấy coin '{coin}'"})

    coin_id = resolved["id"]
    data = coingecko_get(
        f"/coins/{coin_id}/history",
        {"date": date.strip(), "localization": "false"},
    )
    market = data.get("market_data") or {}
    return to_tool_result(
        {
            "resolved": resolved,
            "date": date,
            "market_data": {
                "current_price": market.get("current_price"),
                "market_cap": market.get("market_cap"),
                "total_volume": market.get("total_volume"),
            },
        }
    )


def get_coingecko_history_tool() -> StructuredTool:
    return StructuredTool.from_function(
        name="coingecko_history",
        description=HISTORY,
        func=fetch_history,
        args_schema=HistoryInput,
    )
