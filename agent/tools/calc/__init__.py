"""Calc tools (SymPy)."""

from __future__ import annotations

from langchain_core.tools import BaseTool

from agent.tools.calc.calculus import get_calc_diff_tool, get_calc_integrate_tool
from agent.tools.calc.evaluate import get_calc_evaluate_tool
from agent.tools.calc.percent import get_calc_percent_change_tool
from agent.tools.calc.solve import get_calc_solve_tool


def get_calc_tools() -> list[BaseTool]:
    return [
        get_calc_evaluate_tool(),
        get_calc_solve_tool(),
        get_calc_diff_tool(),
        get_calc_integrate_tool(),
        get_calc_percent_change_tool(),
    ]


__all__ = ["get_calc_tools"]
