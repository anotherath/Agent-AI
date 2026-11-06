"""Helpers SymPy an toàn hơn eval Python thường."""

from __future__ import annotations

import json
from typing import Any

from sympy import N, simplify, sympify
from sympy.core.expr import Expr


def parse_math(expression: str) -> Expr:
    """Parse biểu thức toán bằng SymPy sympify (không dùng eval Python tự do)."""
    text = expression.strip()
    if not text:
        raise ValueError("Biểu thức trống")
    # convert_xor: cho phép 2^10; sympify hạn chế hơn eval builtins
    return sympify(text, convert_xor=True, evaluate=True)


def expr_to_result(
    expr: Any,
    *,
    numeric: bool = False,
    precision: int = 15,
) -> dict[str, Any]:
    """Chuẩn hóa output cho agent."""
    simplified = simplify(expr)
    payload: dict[str, Any] = {
        "symbolic": str(simplified),
        "latex": None,
    }
    try:
        from sympy import latex

        payload["latex"] = latex(simplified)
    except Exception:
        payload["latex"] = str(simplified)

    if numeric:
        try:
            payload["numeric"] = float(N(simplified, precision))
        except Exception:
            payload["numeric"] = str(N(simplified, precision))
    return payload


def to_tool_result(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


# re-export sympify for callers that need it
__all__ = ["parse_math", "expr_to_result", "to_tool_result", "sympify"]
