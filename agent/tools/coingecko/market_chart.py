"""CoinGecko: lịch sử giá / market chart."""

from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from agent.tools.coingecko.client import (
    coingecko_get,
    resolve_coin_id,
    to_tool_result,
)
from agent.tools.coingecko.descriptions import MARKET_CHART


class MarketChartInput(BaseModel):
    coin: str = Field(description="Tên, symbol hoặc id coin")
    vs_currency: str = Field(default="usd")
    days: str = Field(
        default="7",
        description="Số ngày lịch sử, ví dụ: 1, 7, 30, 90, 365, max",
    )


def fetch_market_chart(
    coin: str,
    vs_currency: str = "usd",
    days: str = "7",
) -> str:
    """Gọi /coins/{id}/market_chart — downsample để gọn context."""
    resolved = resolve_coin_id(coin)
    if not resolved or not resolved.get("id"):
        return to_tool_result({"error": f"Không tìm thấy coin '{coin}'"})

    coin_id = resolved["id"]
    vs = (vs_currency or "usd").strip().lower()
    data = coingecko_get(
        f"/coins/{coin_id}/market_chart",
        {"vs_currency": vs, "days": days},
    )

    def _sample(points: list, limit: int = 24) -> list:
        if not points:
            return []
        if len(points) <= limit:
            return points
        step = max(1, len(points) // limit)
        sampled = points[::step][:limit]
        if points[-1] not in sampled:
            sampled.append(points[-1])
        return sampled

    return to_tool_result(
        {
            "resolved": resolved,
            "vs_currency": vs,
            "days": days,
            "prices": _sample(data.get("prices") or []),
            "market_caps": _sample(data.get("market_caps") or []),
            "total_volumes": _sample(data.get("total_volumes") or []),
            "note": "Đã downsample tối đa ~24 điểm để gọn context",
        }
    )


def get_coingecko_market_chart_tool() -> StructuredTool:
    return StructuredTool.from_function(
        name="coingecko_market_chart",
        description=MARKET_CHART,
        func=fetch_market_chart,
        args_schema=MarketChartInput,
    )
