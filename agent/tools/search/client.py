"""Shared Tavily helpers cho search tools."""

from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()

# Giữ nội dung search đầy đủ; chỉ bỏ field nhiễu. Ceiling an toàn nếu 1 hit phình bất thường.
DEFAULT_SEARCH_CONTENT_CHARS = 2500
DEFAULT_SEARCH_ANSWER_CHARS = 2000
DEFAULT_SEARCH_MAX_RESULTS_CAP = 10


def require_api_key() -> str:
    key = os.getenv("TAVILY_API_KEY", "").strip()
    if not key:
        raise ValueError(
            "Missing TAVILY_API_KEY. Set it in the environment or .env file."
        )
    return key


def _normalize(text: str) -> str:
    return " ".join(text.split()).strip()


def _clip(text: str, limit: int) -> str:
    text = _normalize(text)
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def compact_tavily_search_payload(
    *,
    query: str,
    results: list[Any],
    answer: Any = None,
    content_chars: int = DEFAULT_SEARCH_CONTENT_CHARS,
    answer_chars: int = DEFAULT_SEARCH_ANSWER_CHARS,
) -> dict[str, Any]:
    """Giữ title/url/content (+ answer) đầy đủ; bỏ raw_content/id/score."""
    compact_results: list[dict[str, str]] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        url = str(item.get("url") or "").strip()
        content = _clip(str(item.get("content") or ""), content_chars)
        if not (title or url or content):
            continue
        compact_results.append(
            {
                "title": title,
                "url": url,
                "content": content,
            }
        )

    payload: dict[str, Any] = {
        "query": query,
        "results": compact_results,
    }
    if answer is not None and str(answer).strip():
        payload["answer"] = _clip(str(answer), answer_chars)
    return payload


def to_tool_result(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)
