"""Unit tests CoinGecko — mock HTTP, không cần mạng/API key."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from agent.tools.coingecko import get_coingecko_tools
from agent.tools.coingecko.client import _headers, resolve_coin_id, to_tool_result
from agent.tools.coingecko.price import fetch_price


def test_registry_exposes_expected_tools_with_descriptions():
    tools = get_coingecko_tools()
    names = [t.name for t in tools]

    expected = {
        "coingecko_price",
        "coingecko_search",
        "coingecko_trending",
        "coingecko_markets",
        "coingecko_coin_detail",
        "coingecko_market_chart",
        "coingecko_ohlc",
        "coingecko_history",
        "coingecko_global",
        "coingecko_categories",
        "coingecko_exchange_rates",
    }
    assert set(names) == expected
    assert len(names) == len(set(names)), "Tên tool bị trùng"
    for tool in tools:
        assert tool.description and len(tool.description) > 20
        assert tool.name.startswith("coingecko_")


def test_headers_without_api_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("COINGECKO_API_KEY", raising=False)
    headers = _headers()
    assert headers["accept"] == "application/json"
    assert "x-cg-demo-api-key" not in headers
    assert "x-cg-pro-api-key" not in headers


def test_headers_demo_key_only(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("COINGECKO_API_KEY", "CG-test-key-123")
    monkeypatch.setenv("COINGECKO_ENVIRONMENT", "demo")
    headers = _headers()
    assert headers["x-cg-demo-api-key"] == "CG-test-key-123"
    assert "x-cg-pro-api-key" not in headers


def test_headers_pro_key_only(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("COINGECKO_API_KEY", "CG-pro-key-123")
    monkeypatch.setenv("COINGECKO_ENVIRONMENT", "pro")
    headers = _headers()
    assert headers["x-cg-pro-api-key"] == "CG-pro-key-123"
    assert "x-cg-demo-api-key" not in headers


def test_resolve_coin_id_empty_returns_none():
    assert resolve_coin_id("   ") is None
    assert resolve_coin_id("") is None


def test_resolve_coin_id_direct_hit():
    fake = {"id": "bitcoin", "name": "Bitcoin", "symbol": "btc"}
    with patch(
        "agent.tools.coingecko.client.coingecko_get", return_value=fake
    ) as mocked:
        result = resolve_coin_id("bitcoin")
        assert result == {
            "id": "bitcoin",
            "name": "Bitcoin",
            "symbol": "btc",
        }
        mocked.assert_called_once()
        assert mocked.call_args.args[0] == "/coins/bitcoin"


def test_resolve_coin_id_falls_back_to_search_by_symbol():
    request = MagicMock()
    response = MagicMock()
    response.status_code = 404
    error = httpx.HTTPStatusError("not found", request=request, response=response)

    search_payload = {
        "coins": [
            {"id": "ethereum", "name": "Ethereum", "symbol": "eth"},
            {"id": "bitcoin", "name": "Bitcoin", "symbol": "btc"},
        ]
    }

    with patch(
        "agent.tools.coingecko.client.coingecko_get",
        side_effect=[error, search_payload],
    ):
        result = resolve_coin_id("btc")

    assert result == {"id": "bitcoin", "name": "Bitcoin", "symbol": "btc"}


def test_resolve_coin_id_unknown_returns_none():
    request = MagicMock()
    response = MagicMock()
    response.status_code = 404
    error = httpx.HTTPStatusError("not found", request=request, response=response)

    with patch(
        "agent.tools.coingecko.client.coingecko_get",
        side_effect=[error, {"coins": []}],
    ):
        assert resolve_coin_id("not-a-real-coin-xyz") is None


def test_fetch_price_unknown_coin_returns_error_json():
    with patch(
        "agent.tools.coingecko.price.resolve_coin_id", return_value=None
    ):
        raw = fetch_price("nope")
    data = __import__("json").loads(raw)
    assert "error" in data
    assert "nope" in data["error"]


def test_fetch_price_success_shape():
    with (
        patch(
            "agent.tools.coingecko.price.resolve_coin_id",
            return_value={"id": "bitcoin", "name": "Bitcoin", "symbol": "btc"},
        ),
        patch(
            "agent.tools.coingecko.price.coingecko_get",
            return_value={
                "bitcoin": {
                    "usd": 70000,
                    "usd_market_cap": 1.0,
                    "usd_24h_vol": 2.0,
                    "usd_24h_change": -1.5,
                }
            },
        ),
    ):
        data = __import__("json").loads(fetch_price("btc", "usd"))

    assert data["resolved"]["id"] == "bitcoin"
    assert data["price"]["usd"] == 70000
    assert data["price"]["usd_24h_change"] == -1.5


def test_to_tool_result_is_valid_json():
    raw = to_tool_result({"a": 1, "b": "x"})
    assert raw == '{"a": 1, "b": "x"}'
