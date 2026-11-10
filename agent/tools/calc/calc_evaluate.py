"""Tool: calc_evaluate — tính giá trị biểu thức."""

from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from agent.tools.calc.descriptions import (
    CALC_EVALUATE,
    CALC_EVALUATE_EXPRESSION,
    CALC_EVALUATE_NUMERIC,
)
from agent.tools.calc.safe import expr_to_result, parse_math, to_tool_result


class EvaluateInput(BaseModel):
    expression: str = Field(description=CALC_EVALUATE_EXPRESSION)
    numeric: bool = Field(default=True, description=CALC_EVALUATE_NUMERIC)


def calc_evaluate(expression: str, numeric: bool = True) -> str:
    """Tính giá trị biểu thức bằng SymPy."""
    try:
        expr = parse_math(expression)
        return to_tool_result(
            {"expression": expression, **expr_to_result(expr, numeric=numeric)}
        )
    except Exception as exc:  # noqa: BLE001
        return to_tool_result({"error": str(exc), "expression": expression})


def get_calc_evaluate_tool() -> StructuredTool:
    return StructuredTool.from_function(
        name="calc_evaluate",
        description=CALC_EVALUATE,
        func=calc_evaluate,
        args_schema=EvaluateInput,
    )
