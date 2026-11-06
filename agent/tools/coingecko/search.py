"""CoinGecko: search coins / categories / exchanges."""

from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from agent.tools.coingecko.client import coingecko_get, to_tool_result
from agent.tools.coingecko.descriptions import SEARCH


class SearchInput(BaseModel):
    query: str = Field(description="Từ khóa tìm kiếm")


def fetch_search(query: str) -> str:
    """Gọi /search."""
    data = coingecko_get("/search", {"query": query.strip()})
    # Giữ gọn để khỏi phình context
    coins = [
        {
            "id": c.get("id"),
            "name": c.get("name"),
            "symbol": c.get("symbol"),
            "market_cap_rank": c.get("market_cap_rank"),
        }
        for c in (data.get("coins") or [])[:15]
    ]
    categories = [
        {"id": c.get("id"), "name": c.get("name")}
        for c in (data.get("categories") or [])[:10]
    ]
    exchanges = [
        {"id": e.get("id"), "name": e.get("name"), "market_type": e.get("market_type")}
        for e in (data.get("exchanges") or [])[:10]
    ]
    return to_tool_result(
        {"coins": coins, "categories": categories, "exchanges": exchanges}
    )


def get_coingecko_search_tool() -> StructuredTool:
    return StructuredTool.from_function(
        name="coingecko_search",
        description=SEARCH,
        func=fetch_search,
        args_schema=SearchInput,
    )
