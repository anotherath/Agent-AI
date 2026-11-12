"""Shared Tavily helpers cho search tools."""

from __future__ import annotations

import json
import os
import re
from typing import Any

from dotenv import load_dotenv

load_dotenv()

# Giữ nội dung search đầy đủ; chỉ bỏ field nhiễu. Ceiling an toàn nếu 1 hit phình bất thường.
DEFAULT_SEARCH_CONTENT_CHARS = 2500
DEFAULT_SEARCH_ANSWER_CHARS = 2000
DEFAULT_SEARCH_MAX_RESULTS_CAP = 10
DEFAULT_EXTRACT_CONTENT_CHARS = 6000

_MD_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_MD_LINK_JS = re.compile(r"\[([^\]]*)\]\(\s*javascript:[^)]*\)", re.IGNORECASE)
_HTML_TAG = re.compile(r"<[^>]+>")
_MULTI_NL = re.compile(r"\n{3,}")
_BARE_MEDIA_URL = re.compile(
    r"https?://\S+\.(?:png|jpe?g|gif|svg|webp|ico)(?:\?\S*)?",
    re.IGNORECASE,
)


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


def clean_extract_text(text: str) -> str:
    """Bỏ chrome trang (ảnh markdown, JS link, HTML) — giữ text đọc được."""
    if not text:
        return ""
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = _MD_IMAGE.sub("", cleaned)
    cleaned = _MD_LINK_JS.sub(r"\1", cleaned)
    cleaned = _HTML_TAG.sub(" ", cleaned)
    cleaned = _BARE_MEDIA_URL.sub("", cleaned)

    lines: list[str] = []
    for line in cleaned.split("\n"):
        s = line.strip()
        if not s:
            if lines and lines[-1] != "":
                lines.append("")
            continue
        # Bỏ dòng chỉ còn markdown link ảnh / URL media
        if s.startswith("![") or s.startswith("]("):
            continue
        low = s.lower()
        if low in {"đăng nhập", "login", "sign in", "đăng ký", "register"}:
            continue
        if low.startswith("chia sẻ") or low.startswith("share "):
            continue
        lines.append(s)

    cleaned = "\n".join(lines)
    cleaned = _MULTI_NL.sub("\n\n", cleaned)
    return cleaned.strip()


def compact_tavily_extract_payload(
    *,
    url: str,
    title: str | None,
    content: str,
    extract_depth: str,
    format: str,
    content_chars: int = DEFAULT_EXTRACT_CONTENT_CHARS,
) -> dict[str, Any]:
    """Payload gọn cho agent: url/title/content sạch, không dump results thô."""
    cleaned = clean_extract_text(content)
    # Clip theo ký tự (giữ newline đã clean; không flatten hết như search snippet).
    if len(cleaned) > content_chars:
        cleaned = cleaned[:content_chars].rstrip() + "…"
    payload: dict[str, Any] = {
        "url": url,
        "extract_depth": extract_depth,
        "format": format,
        "content": cleaned,
    }
    if title and str(title).strip():
        payload["title"] = str(title).strip()
    return payload


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
