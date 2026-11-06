"""CoinGecko: chi tiết 1 coin."""

from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from agent.tools.coingecko.client import (
    coingecko_get,
    resolve_coin_id,
    to_tool_result,
)
from agent.tools.coingecko.descriptions import COIN_DETAIL


class CoinDetailInput(BaseModel):
    coin: str = Field(description="Tên, symbol hoặc id coin")


def fetch_coin_detail(coin: str) -> str:
    """Gọi /coins/{id} (đã rút gọn field)."""
    resolved = resolve_coin_id(coin)
    if not resolved or not resolved.get("id"):
        return to_tool_result({"error": f"Không tìm thấy coin '{coin}'"})

    coin_id = resolved["id"]
    data = coingecko_get(
        f"/coins/{coin_id}",
        {
            "localization": "false",
            "tickers": "false",
            "market_data": "true",
            "community_data": "false",
            "developer_data": "false",
            "sparkline": "false",
        },
    )
    market = data.get("market_data") or {}
    description = (data.get("description") or {}).get("en") or ""
    if len(description) > 800:
        description = description[:800] + "..."

    payload = {
        "id": data.get("id"),
        "symbol": data.get("symbol"),
        "name": data.get("name"),
        "categories": data.get("categories"),
        "genesis_date": data.get("genesis_date"),
        "homepage": (data.get("links") or {}).get("homepage"),
        "description_en": description,
        "market_data": {
            "current_price_usd": (market.get("current_price") or {}).get("usd"),
            "market_cap_usd": (market.get("market_cap") or {}).get("usd"),
            "total_volume_usd": (market.get("total_volume") or {}).get("usd"),
            "ath_usd": (market.get("ath") or {}).get("usd"),
            "atl_usd": (market.get("atl") or {}).get("usd"),
            "circulating_supply": market.get("circulating_supply"),
            "total_supply": market.get("total_supply"),
            "price_change_percentage_24h": market.get("price_change_percentage_24h"),
            "price_change_percentage_7d": market.get("price_change_percentage_7d"),
            "price_change_percentage_30d": market.get("price_change_percentage_30d"),
        },
    }
    return to_tool_result(payload)


def get_coingecko_coin_detail_tool() -> StructuredTool:
    return StructuredTool.from_function(
        name="coingecko_coin_detail",
        description=COIN_DETAIL,
        func=fetch_coin_detail,
        args_schema=CoinDetailInput,
    )
