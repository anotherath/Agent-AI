"""Unit tests cho $stepN.path resolve."""

from __future__ import annotations

import json

import pytest

from agent.nodes.util.arg_resolution import resolve_args, resolve_value


def test_resolve_literal():
    assert resolve_value("hello", []) == "hello"
    assert resolve_args({"x": 1}, []) == {"x": 1}


def test_resolve_step_path():
    results = [
        {
            "step": 0,
            "tool": "calc_percent_change",
            "args": {},
            "result": json.dumps({"percent_change": 25.0}),
            "ok": True,
        }
    ]
    assert resolve_value("$step0.percent_change", results) == 25.0
    assert resolve_args({"pct": "$step0.percent_change"}, results) == {"pct": 25.0}


def test_resolve_nested_and_missing():
    results = [
        {
            "step": 0,
            "tool": "time_now",
            "args": {},
            "result": {"now": {"iso": "2026-01-01"}},
            "ok": True,
        }
    ]
    assert resolve_value("$step0.now.iso", results) == "2026-01-01"
    with pytest.raises(KeyError):
        resolve_value("$step1.x", results)
    with pytest.raises(KeyError):
        resolve_value("$step0.missing", results)


def test_resolve_inline_template():
    results = [
        {
            "step": 0,
            "tool": "time_now",
            "args": {},
            "result": json.dumps({"now": {"date_dmy": "12-11-2026"}}),
            "ok": True,
        }
    ]
    assert (
        resolve_value("thời tiết Hà Nội ngày $step0.now.date_dmy", results)
        == "thời tiết Hà Nội ngày 12-11-2026"
    )
    assert resolve_args(
        {"query": "thời tiết Hà Nội ngày $step0.now.date_dmy"},
        results,
    ) == {"query": "thời tiết Hà Nội ngày 12-11-2026"}


def test_resolve_inline_multiple_refs():
    results = [
        {
            "step": 0,
            "tool": "time_now",
            "args": {},
            "result": {"now": {"date_dmy": "12-11-2026"}},
            "ok": True,
        },
        {
            "step": 1,
            "tool": "time_shift",
            "args": {},
            "result": {"result": {"date_dmy": "12-10-2026"}},
            "ok": True,
        },
    ]
    assert (
        resolve_value(
            "BTC $step0.now.date_dmy vs $step1.result.date_dmy",
            results,
        )
        == "BTC 12-11-2026 vs 12-10-2026"
    )
