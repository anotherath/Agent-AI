"""Resolve `$stepN.path` trong tool_args trước khi invoke."""

from __future__ import annotations

import json
import re
from typing import Any

from agent.state import ToolResult

_STEP_REF = re.compile(r"^\$step(\d+)(?:\.(.+))?$")


def _parse_result(raw: Any) -> Any:
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw
    return raw


def _dig(obj: Any, path: str) -> Any:
    cur: Any = obj
    for part in path.split("."):
        if isinstance(cur, dict):
            if part not in cur:
                raise KeyError(f"Missing path segment {part!r} in {path!r}")
            cur = cur[part]
        elif isinstance(cur, list):
            idx = int(part)
            cur = cur[idx]
        else:
            raise TypeError(f"Cannot dig {part!r} into {type(cur).__name__}")
    return cur


def _result_for_step(tool_results: list[ToolResult], step: int) -> Any:
    for entry in tool_results:
        if entry.get("step") == step:
            return _parse_result(entry.get("result"))
    raise KeyError(f"No tool_results for step {step}")


def resolve_value(value: Any, tool_results: list[ToolResult]) -> Any:
    if isinstance(value, str):
        match = _STEP_REF.match(value.strip())
        if not match:
            return value
        step = int(match.group(1))
        path = match.group(2)
        payload = _result_for_step(tool_results, step)
        if path:
            return _dig(payload, path)
        return payload
    if isinstance(value, dict):
        return {k: resolve_value(v, tool_results) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve_value(v, tool_results) for v in value]
    return value


def resolve_args(
    tool_args: dict[str, Any] | None,
    tool_results: list[ToolResult],
) -> dict[str, Any]:
    if not tool_args:
        return {}
    resolved = resolve_value(tool_args, tool_results)
    if not isinstance(resolved, dict):
        raise TypeError("Resolved tool_args must be a dict")
    return resolved


__all__ = ["resolve_args", "resolve_value"]
