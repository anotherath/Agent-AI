"""Tool: đạo hàm / tích phân."""

from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from sympy import Symbol, diff, integrate

from agent.tools.calc.descriptions import DIFF, INTEGRATE
from agent.tools.calc.safe import expr_to_result, parse_math, to_tool_result


class DiffInput(BaseModel):
    expression: str = Field(description="Biểu thức, ví dụ: x**3 + 2*x")
    variable: str = Field(default="x")
    order: int = Field(default=1, ge=1, le=5, description="Bậc đạo hàm")


class IntegrateInput(BaseModel):
    expression: str = Field(description="Biểu thức, ví dụ: x**2")
    variable: str = Field(default="x")
    lower: str | None = Field(
        default=None, description="Cận dưới (optional), ví dụ: '0'"
    )
    upper: str | None = Field(
        default=None, description="Cận trên (optional), ví dụ: '1'"
    )


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


def calc_integrate(
    expression: str,
    variable: str = "x",
    lower: str | None = None,
    upper: str | None = None,
) -> str:
    """Tích phân bất định hoặc xác định."""
    try:
        var = Symbol(variable.strip() or "x")
        expr = parse_math(expression)
        if lower is not None and upper is not None:
            result = integrate(expr, (var, parse_math(lower), parse_math(upper)))
            definite = True
        else:
            result = integrate(expr, var)
            definite = False
        return to_tool_result(
            {
                "expression": expression,
                "variable": str(var),
                "definite": definite,
                "lower": lower,
                "upper": upper,
                **expr_to_result(result, numeric=True),
            }
        )
    except Exception as exc:  # noqa: BLE001
        return to_tool_result({"error": str(exc), "expression": expression})


def get_calc_diff_tool() -> StructuredTool:
    return StructuredTool.from_function(
        name="calc_diff",
        description=DIFF,
        func=calc_diff,
        args_schema=DiffInput,
    )


def get_calc_integrate_tool() -> StructuredTool:
    return StructuredTool.from_function(
        name="calc_integrate",
        description=INTEGRATE,
        func=calc_integrate,
        args_schema=IntegrateInput,
    )
