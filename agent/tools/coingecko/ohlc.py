"""CoinGecko: OHLC candlestick."""

from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from agent.tools.coingecko.client import (
    coingecko_get,
    resolve_coin_id,
    to_tool_result,
)
from agent.tools.coingecko.descriptions import OHLC


class OhlcInput(BaseModel):
    coin: str = Field(description="Tên, symbol hoặc id coin")
    vs_currency: str = Field(default="usd")
    days: int = Field(default=7, description="1 | 7 | 14 | 30 | 90 | 180 | 365")


def fetch_ohlc(coin: str, vs_currency: str = "usd", days: int = 7) -> str:
    """Gọi /coins/{id}/ohlc."""
    resolved = resolve_coin_id(coin)
    if not resolved or not resolved.get("id"):
        return to_tool_result({"error": f"Không tìm thấy coin '{coin}'"})

    coin_id = resolved["id"]
    vs = (vs_currency or "usd").strip().lower()
    data = coingecko_get(
        f"/coins/{coin_id}/ohlc",
        {"vs_currency": vs, "days": days},
    )
    # [timestamp, open, high, low, close]
    candles = [
        {"ts": row[0], "open": row[1], "high": row[2], "low": row[3], "close": row[4]}
        for row in data
        if isinstance(row, list) and len(row) >= 5
    ]
    if len(candles) > 48:
        step = max(1, len(candles) // 48)
        candles = candles[::step][:48]

    return to_tool_result(
        {
            "resolved": resolved,
            "vs_currency": vs,
            "days": days,
            "ohlc": candles,
        }
    )


def get_coingecko_ohlc_tool() -> StructuredTool:
    return StructuredTool.from_function(
        name="coingecko_ohlc",
        description=OHLC,
        func=fetch_ohlc,
        args_schema=OhlcInput,
    )
