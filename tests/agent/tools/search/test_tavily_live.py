"""Live integration test Tavily — cần mạng + TAVILY_API_KEY."""

from __future__ import annotations

import json
import os

import pytest

from agent.tools.search.tavily import get_tavily_search_tool
from tests.conftest import show_tool_result

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    not os.getenv("TAVILY_API_KEY"),
    reason="Thiếu TAVILY_API_KEY trong .env",
)
def test_live_tavily_returns_structured_results():
    tool = get_tavily_search_tool(max_results=2, include_answer=True)
    result = tool.invoke({"query": "What is Bitcoin?"})
    show_tool_result("tavily_search(What is Bitcoin?)", result)

    # Chuẩn hóa về list[dict] nếu có thể
    if isinstance(result, str):
        try:
            parsed = json.loads(result)
        except json.JSONDecodeError:
            parsed = result
    else:
        parsed = result

    if isinstance(parsed, dict) and "results" in parsed:
        items = parsed["results"]
    elif isinstance(parsed, list):
        items = parsed
    else:
        # fallback: vẫn phải là nội dung search thật, không chỉ chuỗi dài
        text = str(result)
        assert "bitcoin" in text.lower()
        assert "http" in text.lower()
        return

    assert isinstance(items, list)
    assert 1 <= len(items) <= 3, f"max_results=2 nhưng nhận {len(items)} items"

    for item in items:
        if isinstance(item, dict):
            url = item.get("url") or item.get("link") or ""
            content = (
                item.get("content")
                or item.get("snippet")
                or item.get("raw_content")
                or ""
            )
            assert url.startswith("http"), f"Thiếu URL hợp lệ: {item}"
            assert len(str(content)) > 30, f"Content quá ngắn: {item}"
        else:
            assert "http" in str(item).lower()
