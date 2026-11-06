"""Tool: giải phương trình."""

from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from sympy import Eq, Symbol, solve

from agent.tools.calc.descriptions import SOLVE
from agent.tools.calc.safe import parse_math, to_tool_result


class SolveInput(BaseModel):
    equation: str = Field(
        description=(
            "Phương trình. Có thể viết 'x**2 - 4' (=0) hoặc 'x**2 - 4 = 0' "
            "hoặc '2*x + 1 = 5'"
        )
    )
    variable: str = Field(default="x", description="Ẩn số cần giải")


def calc_solve(equation: str, variable: str = "x") -> str:
    """Giải phương trình theo một biến."""
    try:
        var = Symbol(variable.strip() or "x")
        text = equation.strip()
        if "=" in text:
            left, right = text.split("=", 1)
            eq = Eq(parse_math(left), parse_math(right))
            solutions = solve(eq, var)
        else:
            solutions = solve(parse_math(text), var)

        return to_tool_result(
            {
                "equation": equation,
                "variable": str(var),
                "solutions": [str(s) for s in solutions],
                "solutions_numeric": [
                    float(s.evalf()) if s.is_number else str(s.evalf())
                    for s in solutions
                ],
            }
        )
    except Exception as exc:  # noqa: BLE001
        return to_tool_result({"error": str(exc), "equation": equation})


def get_calc_solve_tool() -> StructuredTool:
    return StructuredTool.from_function(
        name="calc_solve",
        description=SOLVE,
        func=calc_solve,
        args_schema=SolveInput,
    )
