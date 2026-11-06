"""Shared CoinGecko REST client helpers."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

# Demo/public: api.coingecko.com | Pro: pro-api.coingecko.com
COINGECKO_BASE_URL_DEMO = "https://api.coingecko.com/api/v3"
COINGECKO_BASE_URL_PRO = "https://pro-api.coingecko.com/api/v3"
DEFAULT_TIMEOUT = 20.0


def _api_key() -> str:
    return os.getenv("COINGECKO_API_KEY", "").strip()


def _environment() -> str:
    """
    demo | pro

    - Không set key → dùng public/demo URL, không gắn header.
    - Có key: đọc COINGECKO_ENVIRONMENT (mặc định demo).
    """
    env = os.getenv("COINGECKO_ENVIRONMENT", "demo").strip().lower()
    return "pro" if env == "pro" else "demo"


def get_base_url() -> str:
    if _environment() == "pro" and _api_key():
        return COINGECKO_BASE_URL_PRO
    return COINGECKO_BASE_URL_DEMO


def _headers() -> dict[str, str]:
    """Tạo HTTP headers; chỉ gắn ĐÚNG 1 loại key (demo hoặc pro)."""
    headers = {"accept": "application/json"}
    api_key = _api_key()
    if not api_key:
        return headers

    if _environment() == "pro":
        headers["x-cg-pro-api-key"] = api_key
    else:
        headers["x-cg-demo-api-key"] = api_key
    return headers


def coingecko_get(path: str, params: dict[str, Any] | None = None) -> Any:
    """
    GET tới CoinGecko API và trả JSON.

    path ví dụ: "/simple/price", "/search/trending"
    """
    url = f"{get_base_url()}{path}"
    with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
        response = client.get(url, params=params or {}, headers=_headers())
        response.raise_for_status()
        return response.json()


def resolve_coin_id(coin: str) -> dict[str, Any] | None:
    """
    Đổi tên/symbol/id người dùng nhập thành coin id chuẩn CoinGecko.

    Trả về {id, name, symbol} hoặc None.
    """
    query = coin.strip().lower()
    if not query:
        return None

    try:
        data = coingecko_get(
            f"/coins/{query}",
            {
                "localization": "false",
                "tickers": "false",
                "market_data": "false",
                "community_data": "false",
                "developer_data": "false",
            },
        )
        return {
            "id": data.get("id"),
            "name": data.get("name"),
            "symbol": data.get("symbol"),
        }
    except httpx.HTTPStatusError:
        pass

    try:
        search = coingecko_get("/search", {"query": query})
    except httpx.HTTPStatusError:
        return None

    coins = search.get("coins") or []
    if not coins:
        return None

    for item in coins:
        if str(item.get("symbol", "")).lower() == query:
            return {
                "id": item.get("id"),
                "name": item.get("name"),
                "symbol": item.get("symbol"),
            }

    best = coins[0]
    return {
        "id": best.get("id"),
        "name": best.get("name"),
        "symbol": best.get("symbol"),
    }


def to_tool_result(data: Any) -> str:
    """Serialize kết quả API thành JSON string cho agent."""
    return json.dumps(data, ensure_ascii=False, default=str)
