"""Run LangGraph and yield SSE-oriented events (no FastAPI imports)."""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from typing import Any

from agent.graph import get_compiled_graph
from agent.models import llm_model_scope
from agent.state import AgentState, initial_state
from app.services.langfuse_tracing import chat_turn_trace, flush_langfuse

NODE_KIND: dict[str, str] = {
    "orchestrator": "route",
    "tool_select": "tool",
    "tool_execution": "tool",
    "planner": "plan",
    "plan_execution": "plan",
    "gather_review": "plan",
    "generate": "generate",
    "input_guard": "guard",
    "output_guard": "guard",
    "retrieve": "retrieve",
    "rerank": "retrieve",
}


def _chunk_text(chunk: Any) -> str:
    content = getattr(chunk, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
            else:
                parts.append(str(block))
        return "".join(parts)
    if content is None:
        return ""
    return str(content)


def _preview(value: Any, *, limit: int = 160) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        text = value
    else:
        text = json.dumps(value, ensure_ascii=False, default=str)
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[:limit] + "…"


def _open_step_id(open_steps: dict[str, str], lg_node: str | None) -> str | None:
    if not lg_node:
        return None
    return open_steps.get(lg_node)


async def iter_agent_events(
    *,
    query: str,
    user_id: str,
    history: list[dict[str, str]],
    run_id: str | None = None,
    session_id: str | None = None,
    model: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Yield step_* + token message_delta (generate) + message_completed."""
    rid = run_id or str(uuid.uuid4())
    graph = get_compiled_graph()
    catalog_model = (model or "").strip() or None
    state: AgentState = initial_state(
        query, user_id=user_id, messages=history, model=catalog_model
    )
    steps: list[dict[str, Any]] = []
    open_steps: dict[str, str] = {}
    final_answer_parts: list[str] = []
    token_streamed = False

    try:
        with llm_model_scope(catalog_model), chat_turn_trace(
            query=query,
            user_id=user_id,
            session_id=session_id,
            run_id=rid,
        ) as lg_ctx:
            lg_config = lg_ctx.get("config") or None
            async for event in graph.astream_events(
                state,
                config=lg_config or None,
                version="v2",
            ):
                kind = event.get("event")
                name = event.get("name") or ""
                meta = event.get("metadata") or {}
                lg_node = meta.get("langgraph_node")
                data = event.get("data") or {}

                if kind == "on_chain_start" and name in NODE_KIND:
                    step_id = str(uuid.uuid4())
                    open_steps[name] = step_id
                    yield {
                        "event": "step_started",
                        "data": {
                            "step_id": step_id,
                            "kind": NODE_KIND[name],
                            "name": name,
                            "title": name,
                        },
                    }
                    continue

                if kind == "on_chain_end" and name in NODE_KIND:
                    step_id = open_steps.pop(name, str(uuid.uuid4()))
                    output = data.get("output")
                    if (
                        isinstance(output, dict)
                        and output.get("answer")
                        and not token_streamed
                    ):
                        final_answer_parts.append(str(output["answer"]))
                    summary = _summarize_node(name, output)
                    step_row = {
                        "step_id": step_id,
                        "kind": NODE_KIND[name],
                        "name": name,
                        "status": "ok",
                        "summary": summary,
                    }
                    steps.append(step_row)
                    yield {"event": "step_finished", "data": {**step_row}}
                    continue

                # Mid-step progress: tool invoke inside a graph node.
                if kind == "on_tool_start":
                    step_id = _open_step_id(open_steps, lg_node)
                    if step_id:
                        yield {
                            "event": "step_delta",
                            "data": {
                                "step_id": step_id,
                                "text": f"Using · {name}",
                                "payload": {
                                    "phase": "tool_start",
                                    "tool": name,
                                    "input": data.get("input"),
                                },
                            },
                        }
                    continue

                if kind == "on_tool_end":
                    step_id = _open_step_id(open_steps, lg_node)
                    if step_id:
                        preview = _preview(data.get("output"))
                        yield {
                            "event": "step_delta",
                            "data": {
                                "step_id": step_id,
                                "text": f"Using · {name}",
                                "payload": {
                                    "phase": "tool_end",
                                    "tool": name,
                                    "output_preview": preview,
                                },
                            },
                        }
                    continue

                # Mid-step progress: LLM work in non-generate nodes (avoid token spam).
                if (
                    kind == "on_chat_model_start"
                    and lg_node in NODE_KIND
                    and lg_node != "generate"
                ):
                    step_id = _open_step_id(open_steps, lg_node)
                    if step_id:
                        label = {
                            "orchestrator": "Orchestrating",
                            "planner": "Planning next moves",
                            "gather_review": "Reviewing",
                            "retrieve": "Retrieving",
                            "rerank": "Reranking",
                        }.get(lg_node, "Thinking")
                        yield {
                            "event": "step_delta",
                            "data": {
                                "step_id": step_id,
                                "text": label,
                                "payload": {
                                    "phase": "llm_start",
                                    "node": lg_node,
                                },
                            },
                        }
                    continue

                if kind == "on_chat_model_stream" and lg_node == "generate":
                    chunk = data.get("chunk")
                    delta = _chunk_text(chunk)
                    if not delta:
                        continue
                    token_streamed = True
                    final_answer_parts.append(delta)
                    yield {
                        "event": "message_delta",
                        "data": {"delta": delta},
                    }

            final_answer = "".join(final_answer_parts).strip()
            lg_ctx["answer"] = final_answer
            if final_answer and not token_streamed:
                yield {
                    "event": "message_delta",
                    "data": {"delta": final_answer},
                }
            yield {
                "event": "message_completed",
                "data": {
                    "content": final_answer,
                    "run_id": rid,
                    "steps": steps,
                },
            }
    except Exception as exc:  # noqa: BLE001
        yield {
            "event": "error",
            "data": {"code": "agent_error", "detail": str(exc)},
        }
    finally:
        flush_langfuse()


def _summarize_node(node_name: str, payload: Any) -> str:
    if not isinstance(payload, dict):
        return node_name
    if node_name == "orchestrator" and payload.get("route") is not None:
        route = payload["route"]
        route_name = getattr(route, "route", None) or (
            route.get("route") if isinstance(route, dict) else None
        )
        return f"route={route_name}"
    if node_name == "generate" and payload.get("answer"):
        text = str(payload["answer"])
        return text[:120] + ("…" if len(text) > 120 else "")
    if "tool_results" in payload and payload["tool_results"]:
        last = payload["tool_results"][-1]
        tool = last.get("tool") if isinstance(last, dict) else None
        return f"tool={tool}" if tool else "tools updated"
    return node_name


__all__ = ["iter_agent_events", "NODE_KIND"]
