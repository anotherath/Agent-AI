"""Resolve `$stepN.path` trong tool_args trước khi invoke."""

from __future__ import annotations

import json
import re
from typing import Any

from agent.state import ToolResult

# Cả chuỗi là một reference → giữ type gốc (int/float/dict/…).
_STEP_REF_FULL = re.compile(r"^\$step(\d+)(?:\.(.+))?$")
# Reference nằm trong / hoặc bằng cả chuỗi (dùng cho template).
_STEP_REF_INLINE = re.compile(r"\$step(\d+)(?:\.([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*))?")


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


def _lookup(step: int, path: str | None, tool_results: list[ToolResult]) -> Any:
    payload = _result_for_step(tool_results, step)
    if path:
        return _dig(payload, path)
    return payload


def _format_embedded(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return str(value)


def resolve_value(value: Any, tool_results: list[ToolResult]) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        full = _STEP_REF_FULL.match(stripped)
        if full:
            return _lookup(int(full.group(1)), full.group(2), tool_results)

        if _STEP_REF_INLINE.search(value):

            def _replace(match: re.Match[str]) -> str:
                return _format_embedded(
                    _lookup(int(match.group(1)), match.group(2), tool_results)
                )

            return _STEP_REF_INLINE.sub(_replace, value)

        return value
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
