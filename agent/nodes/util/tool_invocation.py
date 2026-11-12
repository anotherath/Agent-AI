"""Helper tool_invocation — gọi tool + ghi ToolResult."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel

from agent.models import get_chat_model
from agent.nodes.util.arg_resolution import resolve_args
from agent.state import ToolResult
from agent.tools.registry import get_tool


def _result_ok(raw: Any) -> bool:
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return True
        if isinstance(data, dict) and data.get("error"):
            return False
    if isinstance(raw, dict) and raw.get("error"):
        return False
    return True


def _fill_args_with_llm(tool: BaseTool, query: str) -> dict[str, Any]:
    schema = tool.args_schema
    if schema is None or not issubclass(schema, BaseModel):
        return {}
    llm = get_chat_model().with_structured_output(schema)
    filled = llm.invoke(
        [
            {
                "role": "system",
                "content": (
                    f"Điền args cho tool `{tool.name}` từ query. "
                    f"Mô tả tool: {tool.description}"
                ),
            },
            {"role": "user", "content": query},
        ]
    )
    if isinstance(filled, BaseModel):
        return filled.model_dump()
    if isinstance(filled, dict):
        return filled
    return {}


def invoke_named_tool(
    *,
    tool_name: str,
    tool_args: dict[str, Any] | None,
    query: str,
    tool_results: list[ToolResult],
    step: int,
) -> ToolResult:
    try:
        tool = get_tool(tool_name)
    except KeyError as exc:
        return {
            "step": step,
            "tool": tool_name,
            "args": tool_args or {},
            "result": json.dumps({"error": str(exc)}, ensure_ascii=False),
            "ok": False,
        }

    args = resolve_args(tool_args, tool_results)
    if not args:
        try:
            args = _fill_args_with_llm(tool, query)
        except Exception:  # noqa: BLE001
            args = {}

    try:
        raw = tool.invoke(args)
        ok = _result_ok(raw)
    except Exception as exc:  # noqa: BLE001
        raw = json.dumps({"error": str(exc)}, ensure_ascii=False)
        ok = False

    return {
        "step": step,
        "tool": tool_name,
        "args": args,
        "result": raw,
        "ok": ok,
    }


__all__ = ["invoke_named_tool"]
