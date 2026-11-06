"""CoinGecko REST tools package."""

from __future__ import annotations

from langchain_core.tools import BaseTool

from agent.tools.coingecko.categories import get_coingecko_categories_tool
from agent.tools.coingecko.coin_detail import get_coingecko_coin_detail_tool
from agent.tools.coingecko.exchange_rates import get_coingecko_exchange_rates_tool
from agent.tools.coingecko.global_data import get_coingecko_global_tool
from agent.tools.coingecko.history import get_coingecko_history_tool
from agent.tools.coingecko.market_chart import get_coingecko_market_chart_tool
from agent.tools.coingecko.markets import get_coingecko_markets_tool
from agent.tools.coingecko.ohlc import get_coingecko_ohlc_tool
from agent.tools.coingecko.price import get_coingecko_price_tool
from agent.tools.coingecko.search import get_coingecko_search_tool
from agent.tools.coingecko.trending import get_coingecko_trending_tool


def get_coingecko_tools() -> list[BaseTool]:
    """Registry toàn bộ tool CoinGecko (REST, không MCP)."""
    return [
        get_coingecko_price_tool(),
        get_coingecko_search_tool(),
        get_coingecko_trending_tool(),
        get_coingecko_markets_tool(),
        get_coingecko_coin_detail_tool(),
        get_coingecko_market_chart_tool(),
        get_coingecko_ohlc_tool(),
        get_coingecko_history_tool(),
        get_coingecko_global_tool(),
        get_coingecko_categories_tool(),
        get_coingecko_exchange_rates_tool(),
    ]


__all__ = ["get_coingecko_tools"]
