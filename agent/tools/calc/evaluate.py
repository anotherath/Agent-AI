"""Tool: evaluate biểu thức."""

from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from agent.tools.calc.descriptions import EVALUATE
from agent.tools.calc.safe import expr_to_result, parse_math, to_tool_result


class EvaluateInput(BaseModel):
    expression: str = Field(description="Biểu thức toán, ví dụ: 2*(10+5)/3")
    numeric: bool = Field(
        default=True,
        description="True = thêm kết quả số thực; False = chỉ dạng symbolic",
    )


def calc_evaluate(expression: str, numeric: bool = True) -> str:
    """Tính giá trị biểu thức bằng SymPy."""
    try:
        expr = parse_math(expression)
        return to_tool_result(
            {"expression": expression, **expr_to_result(expr, numeric=numeric)}
        )
    except Exception as exc:  # noqa: BLE001 - trả lỗi cho agent tự sửa
        return to_tool_result({"error": str(exc), "expression": expression})


def get_calc_evaluate_tool() -> StructuredTool:
    return StructuredTool.from_function(
        name="calc_evaluate",
        description=EVALUATE,
        func=calc_evaluate,
        args_schema=EvaluateInput,
    )
