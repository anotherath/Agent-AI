"""Unit tests Tavily — không gọi API thật."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from agent.tools.search import get_search_tools
from agent.tools.search import tavily_extract as tavily_extract_mod
from agent.tools.search import tavily_search as tavily_search_mod
from agent.tools.search.tavily_extract import get_tavily_extract_tool, tavily_extract
from agent.tools.search.tavily_search import get_tavily_search_tool, tavily_search


def test_tavily_search_requires_api_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    with pytest.raises(ValueError, match="TAVILY_API_KEY"):
        get_tavily_search_tool()


def test_tavily_extract_requires_api_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    with pytest.raises(ValueError, match="TAVILY_API_KEY"):
        get_tavily_extract_tool()


def test_tavily_search_metadata(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test-key")
    tool = get_tavily_search_tool()

    assert tool.name == "tavily_search"
    assert len(tool.description) > 30
    assert "query" in tool.args_schema.model_json_schema()["properties"]


def test_tavily_extract_metadata(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test-key")
    tool = get_tavily_extract_tool()

    assert tool.name == "tavily_extract"
    assert "URL" in tool.description or "url" in tool.description.lower()
    assert "url" in tool.args_schema.model_json_schema()["properties"]


def test_search_registry(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test-key")
    names = {t.name for t in get_search_tools()}
    assert names == {"tavily_search", "tavily_extract"}


def test_tavily_search_mocked(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test-key")

    fake_client = MagicMock()
    fake_client.search.return_value = {
        "results": [
            {
                "title": "Bitcoin",
                "url": "https://example.com/btc",
                "content": "Bitcoin is a cryptocurrency " + ("x" * 40),
                "raw_content": "FULL PAGE " + ("y" * 2000),
                "score": 0.99,
                "id": "abc",
            }
        ],
        "answer": "A digital currency.",
    }

    monkeypatch.setattr(tavily_search_mod, "TavilyClient", lambda api_key: fake_client)

    data = json.loads(tavily_search("What is Bitcoin?", max_results=2))
    assert "error" not in data
    assert data["query"] == "What is Bitcoin?"
    assert len(data["results"]) == 1
    hit = data["results"][0]
    assert hit["title"] == "Bitcoin"
    assert hit["url"] == "https://example.com/btc"
    assert "raw_content" not in hit
    assert "score" not in hit
    assert "id" not in hit
    assert "cryptocurrency" in hit["content"]
    assert len(hit["content"]) == len(_normalize_ws(hit["content"]))
    fake_client.search.assert_called_once()
    assert fake_client.search.call_args.kwargs["max_results"] == 2


def _normalize_ws(text: str) -> str:
    return " ".join(text.split()).strip()


def test_tavily_search_caps_max_results(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test-key")
    fake_client = MagicMock()
    fake_client.search.return_value = {"results": [], "answer": ""}
    monkeypatch.setattr(tavily_search_mod, "TavilyClient", lambda api_key: fake_client)

    tavily_search("q", max_results=99)
    assert fake_client.search.call_args.kwargs["max_results"] == 10


def test_tavily_extract_mocked(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test-key")

    fake_client = MagicMock()
    fake_client.extract.return_value = {
        "results": [
            {
                "url": "https://example.com/a",
                "raw_content": "# Hello\n\nWorld " + ("x" * 40),
                "title": "Example",
            }
        ],
        "failed_results": [],
    }

    monkeypatch.setattr(tavily_extract_mod, "TavilyClient", lambda api_key: fake_client)

    data = json.loads(tavily_extract("https://example.com/a"))
    assert "error" not in data
    assert data["url"] == "https://example.com/a"
    assert "Hello" in data["content"]
    fake_client.extract.assert_called_once()
