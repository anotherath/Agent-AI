"""CoinGecko: tỷ giá quy đổi BTC ↔ các currency."""

from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from agent.tools.coingecko.client import coingecko_get, to_tool_result
from agent.tools.coingecko.descriptions import EXCHANGE_RATES


class ExchangeRatesInput(BaseModel):
    currency: str | None = Field(
        default=None,
        description="Lọc 1 currency, ví dụ: usd. Để trống để lấy toàn bộ (rút gọn).",
    )


def fetch_exchange_rates(currency: str | None = None) -> str:
    """Gọi /exchange_rates."""
    data = coingecko_get("/exchange_rates")
    rates = data.get("rates") or {}
    if currency:
        key = currency.strip().lower()
        item = rates.get(key)
        if not item:
            return to_tool_result({"error": f"Không có currency '{key}'"})
        return to_tool_result({"currency": key, "rate": item})

    # Rút gọn: chỉ giữ name + value
    compact = {
        k: {"name": v.get("name"), "unit": v.get("unit"), "value": v.get("value")}
        for k, v in list(rates.items())[:40]
    }
    return to_tool_result({"rates": compact})


def get_coingecko_exchange_rates_tool() -> StructuredTool:
    return StructuredTool.from_function(
        name="coingecko_exchange_rates",
        description=EXCHANGE_RATES,
        func=fetch_exchange_rates,
        args_schema=ExchangeRatesInput,
    )
