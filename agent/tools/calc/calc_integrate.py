"""Tool: calc_integrate — tích phân."""

from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from sympy import Symbol, integrate

from agent.tools.calc.descriptions import (
    CALC_INTEGRATE,
    CALC_INTEGRATE_EXPRESSION,
    CALC_INTEGRATE_LOWER,
    CALC_INTEGRATE_UPPER,
    CALC_INTEGRATE_VARIABLE,
)
from agent.tools.calc.safe import expr_to_result, parse_math, to_tool_result


class IntegrateInput(BaseModel):
    expression: str = Field(description=CALC_INTEGRATE_EXPRESSION)
    variable: str = Field(default="x", description=CALC_INTEGRATE_VARIABLE)
    lower: str | None = Field(default=None, description=CALC_INTEGRATE_LOWER)
    upper: str | None = Field(default=None, description=CALC_INTEGRATE_UPPER)


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


def get_calc_integrate_tool() -> StructuredTool:
    return StructuredTool.from_function(
        name="calc_integrate",
        description=CALC_INTEGRATE,
        func=calc_integrate,
        args_schema=IntegrateInput,
    )
