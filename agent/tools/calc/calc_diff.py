"""Tool: calc_diff — đạo hàm."""

from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from sympy import Symbol, diff

from agent.tools.calc.descriptions import (
    CALC_DIFF,
    CALC_DIFF_EXPRESSION,
    CALC_DIFF_ORDER,
    CALC_DIFF_VARIABLE,
)
from agent.tools.calc.safe import expr_to_result, parse_math, to_tool_result


class DiffInput(BaseModel):
    expression: str = Field(description=CALC_DIFF_EXPRESSION)
    variable: str = Field(default="x", description=CALC_DIFF_VARIABLE)
    order: int = Field(default=1, ge=1, le=5, description=CALC_DIFF_ORDER)


def calc_diff(expression: str, variable: str = "x", order: int = 1) -> str:
    """Đạo hàm biểu thức."""
    try:
        var = Symbol(variable.strip() or "x")
        expr = parse_math(expression)
        result = diff(expr, var, order)
        return to_tool_result(
            {
                "expression": expression,
                "variable": str(var),
                "order": order,
                **expr_to_result(result, numeric=False),
            }
        )
    except Exception as exc:  # noqa: BLE001
        return to_tool_result({"error": str(exc), "expression": expression})


def get_calc_diff_tool() -> StructuredTool:
    return StructuredTool.from_function(
        name="calc_diff",
        description=CALC_DIFF,
        func=calc_diff,
        args_schema=DiffInput,
    )
