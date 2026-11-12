"""Rematch từng bước plan: tên tool / args / $stepN / placeholder giả."""

from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, ValidationError

from agent.models import get_chat_model
from agent.nodes.util.arg_resolution import resolve_args
from agent.state import PlanStep, ToolResult
from agent.tools.registry import get_tool, resolve_tool_name
from agent.tools.result_paths import TOOL_RESULT_PATHS

# Jinja/template: {{var}} ; hoặc {var} / {17 ngày trước} — không phải $stepN.
_FAKE_DOUBLE_BRACE = re.compile(r"\{\{[^{}]{1,80}\}\}")
_FAKE_SINGLE_BRACE = re.compile(r"\{(?!\$step)[^{}]{1,80}\}")
_ARGS_ERROR_MARKERS = (
    "validation error",
    "field required",
    "missing",
    "input_value={}",
    "type=missing",
    "placeholder giả",
    "{{",
)


def _walk_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        out: list[str] = []
        for v in value.values():
            out.extend(_walk_strings(v))
        return out
    if isinstance(value, list):
        out = []
        for v in value:
            out.extend(_walk_strings(v))
        return out
    return []


def has_fake_placeholder(tool_args: dict[str, Any] | None) -> bool:
    for text in _walk_strings(tool_args or {}):
        if _FAKE_DOUBLE_BRACE.search(text) or _FAKE_SINGLE_BRACE.search(text):
            return True
    return False


def missing_required_fields(
    tool: BaseTool, args: dict[str, Any]
) -> list[str]:
    schema = tool.args_schema
    if schema is None or not issubclass(schema, BaseModel):
        return []
    missing: list[str] = []
    for name, field in schema.model_fields.items():
        if field.is_required() and name not in args:
            missing.append(name)
    return missing


def try_resolve_args(
    tool_args: dict[str, Any] | None,
    tool_results: list[ToolResult],
) -> tuple[dict[str, Any] | None, str | None]:
    try:
        return resolve_args(tool_args, tool_results), None
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)


def precheck_step_args(
    *,
    tool_name: str,
    tool_args: dict[str, Any] | None,
    tool_results: list[ToolResult],
) -> str | None:
    """Trả về lý do lỗi args (sửa tại chỗ); None nếu tạm ổn để invoke."""
    if has_fake_placeholder(tool_args):
        return (
            "tool_args chứa placeholder giả kiểu `{{var}}` / `{...}` "
            "(cấm; phải dùng literal hoặc `$stepN.path`)."
        )
    resolved, err = try_resolve_args(tool_args, tool_results)
    if err:
        return f"Không resolve được $stepN.path: {err}"
    try:
        tool = get_tool(tool_name)
    except KeyError as exc:
        return str(exc)
    missing = missing_required_fields(tool, resolved or {})
    if missing:
        return f"Thiếu field bắt buộc: {', '.join(missing)}"
    schema = tool.args_schema
    if schema is not None and issubclass(schema, BaseModel) and resolved is not None:
        try:
            schema.model_validate(resolved)
        except ValidationError as exc:
            return f"Args không khớp schema: {exc}"
    return None


def is_args_failure(result_raw: Any) -> bool:
    text = result_raw if isinstance(result_raw, str) else json.dumps(
        result_raw, ensure_ascii=False, default=str
    )
    low = text.lower()
    return any(m in low for m in _ARGS_ERROR_MARKERS)


def _paths_hint() -> str:
    blocks = [f"- {name}: {paths}" for name, paths in TOOL_RESULT_PATHS.items()]
    return "\n".join(blocks) if blocks else "(không có)"


def rematch_step_pick(
    *,
    query: str,
    step: PlanStep,
    messages: list | None,
    pick_single_tool,
) -> tuple[str | None, dict[str, Any]]:
    """Rematch khi thiếu/sai tool_name (dùng pick_single_tool)."""
    purpose = (step.purpose or "").strip()
    pick_query = f"{query}\nBước cần làm: {purpose}" if purpose else query
    # Plan rematch: không cho no_tool (sentinel chỉ dành cho tool_select).
    picked = pick_single_tool(pick_query, messages, allow_no_tool=False)
    resolved = resolve_tool_name(picked.tool_name)
    args = picked.tool_args if picked.tool_args else (step.tool_args or {})
    return resolved, args or {}


def rematch_step_args(
    *,
    query: str,
    step: PlanStep,
    tool_name: str,
    previous_args: dict[str, Any] | None,
    tool_results: list[ToolResult],
    error: str,
) -> dict[str, Any]:
    """LLM điền lại tool_args đúng schema + $stepN từ kết quả bước trước."""
    try:
        tool = get_tool(tool_name)
    except KeyError:
        return previous_args or {}

    schema = tool.args_schema
    if schema is None or not issubclass(schema, BaseModel):
        return previous_args or {}

    purpose = (step.purpose or "").strip() or "(không có)"
    llm = get_chat_model().with_structured_output(schema)
    system = (
        f"Bạn sửa args cho tool `{tool_name}` trong multi-step plan.\n"
        f"Mô tả tool: {tool.description}\n"
        "Quy tắc:\n"
        "- Điền đủ field bắt buộc đúng schema.\n"
        "- Tham chiếu bước trước bằng `$stepN.path` (N từ 0) hoặc chuỗi xen `$stepN.path`.\n"
        "- CẤM placeholder giả: `{{today_date}}`, `{{var}}`, `{17 ngày trước}`, `{tên_biến}`.\n"
        "- Với calc: điền số literal lấy từ tool_results (không để `{{today_sjc_buy}}`).\n"
        "- Không trả lời user; chỉ điền args.\n\n"
        f"Path kết quả tools:\n{_paths_hint()}"
    )
    user = (
        f"Query: {query}\n"
        f"Purpose bước: {purpose}\n"
        f"Args trước: {json.dumps(previous_args or {}, ensure_ascii=False, default=str)}\n"
        f"Lỗi: {error}\n"
        f"Tool results hiện có: "
        f"{json.dumps(tool_results, ensure_ascii=False, default=str)}"
    )
    try:
        filled = llm.invoke(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ]
        )
    except Exception:  # noqa: BLE001
        return previous_args or {}

    if isinstance(filled, BaseModel):
        return filled.model_dump()
    if isinstance(filled, dict):
        return filled
    return previous_args or {}


__all__ = [
    "has_fake_placeholder",
    "missing_required_fields",
    "try_resolve_args",
    "precheck_step_args",
    "is_args_failure",
    "rematch_step_pick",
    "rematch_step_args",
]
