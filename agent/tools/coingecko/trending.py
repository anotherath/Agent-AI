"""CoinGecko: trending coins / NFTs / categories."""

from __future__ import annotations

from langchain_core.tools import StructuredTool

from agent.tools.coingecko.client import coingecko_get, to_tool_result
from agent.tools.coingecko.descriptions import TRENDING


def fetch_trending() -> str:
    """Gọi /search/trending."""
    data = coingecko_get("/search/trending")
    coins = []
    for item in data.get("coins") or []:
        c = item.get("item") or {}
        coins.append(
            {
                "id": c.get("id"),
                "name": c.get("name"),
                "symbol": c.get("symbol"),
                "market_cap_rank": c.get("market_cap_rank"),
                "score": c.get("score"),
                "price_btc": c.get("price_btc"),
            }
        )
    nfts = [
        {
            "id": n.get("id"),
            "name": n.get("name"),
            "symbol": n.get("symbol"),
            "floor_price_in_native_currency": n.get("floor_price_in_native_currency"),
        }
        for n in (data.get("nfts") or [])[:10]
    ]
    categories = data.get("categories") or []
    return to_tool_result({"coins": coins, "nfts": nfts, "categories": categories[:10]})


def get_coingecko_trending_tool() -> StructuredTool:
    return StructuredTool.from_function(
        name="coingecko_trending",
        description=TRENDING,
        func=fetch_trending,
    )
