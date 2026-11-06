"""Unit tests calc tools."""

from __future__ import annotations

import json

from agent.tools.calc import get_calc_tools
from agent.tools.calc.evaluate import calc_evaluate
from agent.tools.calc.percent import calc_percent_change
from agent.tools.calc.solve import calc_solve
from tests.conftest import show_tool_result


def test_calc_registry():
    names = {t.name for t in get_calc_tools()}
    assert names == {
        "calc_evaluate",
        "calc_solve",
        "calc_diff",
        "calc_integrate",
        "calc_percent_change",
    }


def test_calc_evaluate_basic():
    data = json.loads(calc_evaluate("2*(3+4)", numeric=True))
    show_tool_result("calc_evaluate(2*(3+4))", data)
    assert "error" not in data
    assert data["numeric"] == 14


def test_calc_solve_quadratic():
    data = json.loads(calc_solve("x**2 - 4", "x"))
    show_tool_result("calc_solve(x**2 - 4)", data)
    assert set(data["solutions"]) == {"-2", "2"}


def test_calc_percent_change():
    data = json.loads(calc_percent_change(100, 120))
    show_tool_result("calc_percent_change(100->120)", data)
    assert data["percent_change"] == 20.0


def test_calc_evaluate_invalid():
    data = json.loads(calc_evaluate("???"))
    assert "error" in data
