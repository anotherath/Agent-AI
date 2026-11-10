"""Unit tests for step_delta emission in iter_agent_events."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock, patch

from app.services.agent_run import iter_agent_events


class _FakeChunk:
    def __init__(self, content: str) -> None:
        self.content = content


class _NullTrace:
    def __enter__(self) -> dict[str, Any]:
        return {"config": {}, "root": None}

    def __exit__(self, *_args: Any) -> None:
        return None


async def _fake_astream_events(_state: Any, config: Any = None, version: str = "v2"):
    assert version == "v2"
    _ = config
    yield {
        "event": "on_chain_start",
        "name": "orchestrator",
        "metadata": {"langgraph_node": "orchestrator"},
        "data": {},
    }
    yield {
        "event": "on_chat_model_start",
        "name": "ChatModel",
        "metadata": {"langgraph_node": "orchestrator"},
        "data": {},
    }
    yield {
        "event": "on_chain_end",
        "name": "orchestrator",
        "metadata": {"langgraph_node": "orchestrator"},
        "data": {"output": {"route": {"route": "single_tool"}}},
    }
    yield {
        "event": "on_chain_start",
        "name": "single_tool",
        "metadata": {"langgraph_node": "single_tool"},
        "data": {},
    }
    yield {
        "event": "on_tool_start",
        "name": "tavily_search",
        "metadata": {"langgraph_node": "single_tool"},
        "data": {"input": {"query": "cats"}},
    }
    yield {
        "event": "on_tool_end",
        "name": "tavily_search",
        "metadata": {"langgraph_node": "single_tool"},
        "data": {"output": '[{"title":"Cat"}]', "input": {"query": "cats"}},
    }
    yield {
        "event": "on_chain_end",
        "name": "single_tool",
        "metadata": {"langgraph_node": "single_tool"},
        "data": {
            "output": {
                "tool_results": [{"tool": "tavily_search", "ok": True}],
            }
        },
    }
    yield {
        "event": "on_chain_start",
        "name": "generate",
        "metadata": {"langgraph_node": "generate"},
        "data": {},
    }
    yield {
        "event": "on_chat_model_stream",
        "name": "ChatModel",
        "metadata": {"langgraph_node": "generate"},
        "data": {"chunk": _FakeChunk("hello")},
    }
    yield {
        "event": "on_chain_end",
        "name": "generate",
        "metadata": {"langgraph_node": "generate"},
        "data": {"output": {"answer": "hello"}},
    }


def test_iter_agent_events_emits_step_delta() -> None:
    graph = MagicMock()
    graph.astream_events = _fake_astream_events

    async def _collect() -> list[dict[str, Any]]:
        return [
            evt
            async for evt in iter_agent_events(
                query="cats?",
                user_id="u1",
                history=[],
                run_id="run-1",
            )
        ]

    with (
        patch("app.services.agent_run.get_compiled_graph", return_value=graph),
        patch(
            "app.services.agent_run.chat_turn_trace",
            side_effect=lambda **_kwargs: _NullTrace(),
        ),
        patch("app.services.agent_run.flush_langfuse"),
    ):
        events = asyncio.run(_collect())

    kinds = [e["event"] for e in events]
    assert kinds.count("step_delta") >= 3
    assert "step_started" in kinds
    assert "step_finished" in kinds
    assert "message_delta" in kinds
    assert kinds[-1] == "message_completed"

    deltas = [e for e in events if e["event"] == "step_delta"]
    texts = [d["data"]["text"] for d in deltas]
    assert any("Orchestrating" in t for t in texts)
    assert any("Using · tavily_search" in t for t in texts)

    started_ids = {
        e["data"]["step_id"] for e in events if e["event"] == "step_started"
    }
    for d in deltas:
        assert d["data"]["step_id"] in started_ids
