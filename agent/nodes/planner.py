"""Node planner — LLM lập plan[] chi tiết."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, create_model

from agent.models import get_chat_model
from agent.prompts.planner import PLANNER_SYSTEM, PLANNER_USER
from agent.state import AgentState, PlanStep
from agent.tools.registry import (
    known_tool_names_sorted,
    sanitize_plan_steps,
    tool_catalog_text,
    tool_result_paths_text,
)


class PlanOutput(BaseModel):
    steps: list[PlanStep] = Field(default_factory=list)


def _plan_output_schema() -> type[BaseModel]:
    """PlanOutput với tool_name ∈ registry (enum động) trên mỗi bước."""
    names = tuple(known_tool_names_sorted())
    if not names:
        return PlanOutput
    name_type = Literal[*names]  # type: ignore[valid-type]
    step_model = create_model(
        "PlanStepConstrained",
        tool_name=(name_type, ...),
        tool_args=(dict[str, Any], Field(default_factory=dict)),
        purpose=(str, ""),
        __base__=BaseModel,
    )
    return create_model(
        "PlanOutputConstrained",
        steps=(list[step_model], Field(default_factory=list)),
        __base__=BaseModel,
    )


def _parse_steps(result: Any) -> list[PlanStep]:
    if isinstance(result, PlanOutput):
        return list(result.steps)
    if isinstance(result, BaseModel):
        data = result.model_dump()
        return PlanOutput.model_validate(data).steps
    return PlanOutput.model_validate(result).steps


def _steps_need_rematch(steps: list[PlanStep]) -> bool:
    return any(not (s.tool_name or "").strip() for s in steps)


def _invalid_step_hints(steps: list[PlanStep]) -> str:
    hints: list[str] = []
    for i, step in enumerate(steps):
        if (step.tool_name or "").strip():
            continue
        purpose = (step.purpose or "").strip() or "(không có purpose)"
        hints.append(f"  - step{i}: {purpose}")
    return "\n".join(hints) if hints else "  - (không rõ)"


def planner_node(state: AgentState) -> dict[str, Any]:
    query = state.get("query") or ""
    route = state.get("route")
    route_hint = ""
    if route is not None:
        route_hint = route.model_dump_json()

    schema = _plan_output_schema()
    llm = get_chat_model().with_structured_output(schema)
    system = PLANNER_SYSTEM.format(
        tool_catalog=tool_catalog_text(),
        tool_result_paths=tool_result_paths_text(),
    )
    user = PLANNER_USER.format(
        query=query,
        route_hint=route_hint or "(không)",
        tool_results=state.get("tool_results") or [],
    )
    allowed = ", ".join(known_tool_names_sorted()) or "(không có)"

    result = llm.invoke(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
    )
    steps = sanitize_plan_steps(_parse_steps(result))

    # Rematch cả plan tối đa 1 lần nếu còn tool_name trống sau sanitize.
    # Sửa args/$stepN từng bước: plan_execution + PLANNER_MAX_RETRIES.
    if _steps_need_rematch(steps):
        retry_user = (
            f"{user}\n\n"
            f"Lỗi: các bước sau có tool_name không hợp lệ hoặc trống:\n"
            f"{_invalid_step_hints(steps)}\n"
            f"Viết lại toàn bộ steps; mỗi bước chỉ được chọn đúng một tên trong: {allowed}."
        )
        result2 = llm.invoke(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": retry_user},
            ]
        )
        steps = sanitize_plan_steps(_parse_steps(result2))

    return {
        "plan": steps,
        "step_index": 0,
        "after_tool_next": "gather_review",
    }


__all__ = ["planner_node"]
