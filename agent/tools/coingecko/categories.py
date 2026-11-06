"""CoinGecko: danh mục coin (DeFi, Layer-1, meme...)."""

from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from agent.tools.coingecko.client import coingecko_get, to_tool_result
from agent.tools.coingecko.descriptions import CATEGORIES


class CategoriesInput(BaseModel):
    order: str = Field(
        default="market_cap_desc",
        description="market_cap_desc | market_cap_asc | name_desc | name_asc | ...",
    )
    limit: int = Field(default=20, ge=1, le=50)


def fetch_categories(order: str = "market_cap_desc", limit: int = 20) -> str:
    """Gọi /coins/categories."""
    data = coingecko_get("/coins/categories", {"order": order})
    rows = [
        {
            "id": c.get("id"),
            "name": c.get("name"),
            "market_cap": c.get("market_cap"),
            "market_cap_change_24h": c.get("market_cap_change_24h"),
            "volume_24h": c.get("volume_24h"),
            "top_3_coins": c.get("top_3_coins"),
        }
        for c in data[:limit]
    ]
    return to_tool_result({"categories": rows})


def get_coingecko_categories_tool() -> StructuredTool:
    return StructuredTool.from_function(
        name="coingecko_categories",
        description=CATEGORIES,
        func=fetch_categories,
        args_schema=CategoriesInput,
    )
