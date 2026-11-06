"""CoinGecko: giá realtime theo coin id/symbol."""

from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from agent.tools.coingecko.client import (
    coingecko_get,
    resolve_coin_id,
    to_tool_result,
)
from agent.tools.coingecko.descriptions import PRICE


class PriceInput(BaseModel):
    coin: str = Field(description="Tên, symbol hoặc id coin, ví dụ: btc, bitcoin")
    vs_currency: str = Field(default="usd", description="Đơn vị: usd, vnd, eur, ...")
    include_market_cap: bool = Field(default=True)
    include_24hr_vol: bool = Field(default=True)
    include_24hr_change: bool = Field(default=True)


def fetch_price(
    coin: str,
    vs_currency: str = "usd",
    include_market_cap: bool = True,
    include_24hr_vol: bool = True,
    include_24hr_change: bool = True,
) -> str:
    """Resolve coin rồi gọi /simple/price."""
    resolved = resolve_coin_id(coin)
    if not resolved or not resolved.get("id"):
        return to_tool_result({"error": f"Không tìm thấy coin '{coin}'"})

    coin_id = resolved["id"]
    vs = (vs_currency or "usd").strip().lower()
    data = coingecko_get(
        "/simple/price",
        {
            "ids": coin_id,
            "vs_currencies": vs,
            "include_market_cap": str(include_market_cap).lower(),
            "include_24hr_vol": str(include_24hr_vol).lower(),
            "include_24hr_change": str(include_24hr_change).lower(),
            "include_last_updated_at": "true",
        },
    )
    return to_tool_result({"resolved": resolved, "price": data.get(coin_id, data)})


def get_coingecko_price_tool() -> StructuredTool:
    return StructuredTool.from_function(
        name="coingecko_price",
        description=PRICE,
        func=fetch_price,
        args_schema=PriceInput,
    )
