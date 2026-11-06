"""Live integration tests CoinGecko — cần mạng; key optional."""

from __future__ import annotations

import json

import pytest

from agent.tools.coingecko.markets import get_coingecko_markets_tool
from agent.tools.coingecko.price import get_coingecko_price_tool
from agent.tools.coingecko.search import get_coingecko_search_tool
from agent.tools.coingecko.trending import get_coingecko_trending_tool
from tests.conftest import show_tool_result

pytestmark = pytest.mark.integration


def _parse(result: str) -> dict:
    data = json.loads(result)
    assert isinstance(data, dict)
    return data


def test_live_price_btc_has_usable_market_fields():
    tool = get_coingecko_price_tool()
    raw = tool.invoke(
        {
            "coin": "btc",
            "vs_currency": "usd",
            "include_market_cap": True,
            "include_24hr_vol": True,
            "include_24hr_change": True,
        }
    )
    data = _parse(raw)
    show_tool_result("coingecko_price(btc, usd)", data)

    assert "error" not in data
    assert data["resolved"]["id"] == "bitcoin"
    assert data["resolved"]["symbol"].lower() == "btc"

    price = data["price"]
    assert isinstance(price["usd"], (int, float))
    assert 1000 < price["usd"] < 1_000_000  # sanity bound, không chỉ > 0
    assert "usd_market_cap" in price
    assert price["usd_market_cap"] > price["usd"]
    assert "usd_24h_vol" in price
    assert price["usd_24h_vol"] > 0
    assert "usd_24h_change" in price
    assert isinstance(price["usd_24h_change"], (int, float))


def test_live_price_unknown_coin_returns_error():
    tool = get_coingecko_price_tool()
    data = _parse(tool.invoke({"coin": "xyzzycoin999"}))
    show_tool_result("coingecko_price(unknown)", data)
    assert "error" in data


def test_live_trending_has_ranked_coins():
    tool = get_coingecko_trending_tool()
    data = _parse(tool.invoke({}))
    show_tool_result("coingecko_trending", data)

    assert isinstance(data.get("coins"), list)
    assert len(data["coins"]) >= 1, "Trending không được rỗng"
    first = data["coins"][0]
    assert first.get("id")
    assert first.get("symbol")
    assert first.get("name")


def test_live_markets_top_has_ordered_ranks():
    tool = get_coingecko_markets_tool()
    data = _parse(
        tool.invoke(
            {
                "vs_currency": "usd",
                "per_page": 5,
                "page": 1,
                "order": "market_cap_desc",
            }
        )
    )
    show_tool_result("coingecko_markets(top 5)", data)

    markets = data["markets"]
    assert len(markets) == 5
    ranks = [m["market_cap_rank"] for m in markets if m.get("market_cap_rank")]
    assert ranks == sorted(ranks), "market_cap_desc phải tăng dần theo rank"
    assert markets[0]["current_price"] > 0
    assert markets[0]["market_cap"] > markets[0]["current_price"]


def test_live_search_bitcoin_finds_bitcoin_id():
    tool = get_coingecko_search_tool()
    data = _parse(tool.invoke({"query": "bitcoin"}))
    show_tool_result("coingecko_search(bitcoin)", data)

    coins = data.get("coins") or []
    assert coins, "Search 'bitcoin' phải có kết quả"
    ids = {c.get("id") for c in coins}
    assert "bitcoin" in ids
