"""Unit tests Tavily — không gọi API thật."""

from __future__ import annotations

import pytest

from agent.tools.search.tavily import get_tavily_search_tool


def test_tavily_requires_api_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    with pytest.raises(ValueError, match="TAVILY_API_KEY"):
        get_tavily_search_tool()


def test_tavily_tool_metadata(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test-key")
    tool = get_tavily_search_tool(max_results=3)

    assert tool.name == "tavily_search"
    assert "Tavily" in tool.description or "tìm kiếm" in tool.description.lower()
    assert len(tool.description) > 30
