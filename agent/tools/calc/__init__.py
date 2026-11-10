"""Calc tools (SymPy)."""

from __future__ import annotations

from langchain_core.tools import BaseTool

from agent.tools.calc.calc_diff import get_calc_diff_tool
from agent.tools.calc.calc_evaluate import get_calc_evaluate_tool
from agent.tools.calc.calc_integrate import get_calc_integrate_tool
from agent.tools.calc.calc_percent_change import get_calc_percent_change_tool
from agent.tools.calc.calc_solve import get_calc_solve_tool


def get_calc_tools() -> list[BaseTool]:
    return [
        get_calc_evaluate_tool(),
        get_calc_solve_tool(),
        get_calc_diff_tool(),
        get_calc_integrate_tool(),
        get_calc_percent_change_tool(),
    ]


__all__ = ["get_calc_tools"]
