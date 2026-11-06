"""CoinGecko: bảng xếp hạng / markets list."""

from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from agent.tools.coingecko.client import coingecko_get, to_tool_result
from agent.tools.coingecko.descriptions import MARKETS


class MarketsInput(BaseModel):
    vs_currency: str = Field(default="usd", description="Đơn vị quy đổi")
    per_page: int = Field(default=10, ge=1, le=50, description="Số coin mỗi trang")
    page: int = Field(default=1, ge=1, description="Trang")
    order: str = Field(
        default="market_cap_desc",
        description="market_cap_desc | volume_desc | id_asc | ...",
    )
    category: str | None = Field(
        default=None,
        description="Lọc theo category id, ví dụ: decentralized-finance-defi",
    )
    sparkline: bool = Field(default=False)


def fetch_markets(
    vs_currency: str = "usd",
    per_page: int = 10,
    page: int = 1,
    order: str = "market_cap_desc",
    category: str | None = None,
    sparkline: bool = False,
) -> str:
    """Gọi /coins/markets."""
    params: dict = {
        "vs_currency": (vs_currency or "usd").strip().lower(),
        "order": order,
        "per_page": per_page,
        "page": page,
        "sparkline": str(sparkline).lower(),
        "price_change_percentage": "24h",
    }
    if category:
        params["category"] = category

    data = coingecko_get("/coins/markets", params)
    rows = [
        {
            "id": c.get("id"),
            "symbol": c.get("symbol"),
            "name": c.get("name"),
            "current_price": c.get("current_price"),
            "market_cap": c.get("market_cap"),
            "market_cap_rank": c.get("market_cap_rank"),
            "total_volume": c.get("total_volume"),
            "price_change_percentage_24h": c.get("price_change_percentage_24h"),
        }
        for c in data
    ]
    return to_tool_result({"vs_currency": params["vs_currency"], "markets": rows})


def get_coingecko_markets_tool() -> StructuredTool:
    return StructuredTool.from_function(
        name="coingecko_markets",
        description=MARKETS,
        func=fetch_markets,
        args_schema=MarketsInput,
    )
