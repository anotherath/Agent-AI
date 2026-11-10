"""Unit tests timeutil tools."""

from __future__ import annotations

import json

from agent.tools.timeutil import get_timeutil_tools
from agent.tools.timeutil.time_convert import time_convert
from agent.tools.timeutil.time_now import time_now
from agent.tools.timeutil.time_shift import time_shift
from tests.conftest import show_tool_result


def test_timeutil_registry():
    names = {t.name for t in get_timeutil_tools()}
    assert names == {
        "time_now",
        "time_convert",
        "time_shift",
    }


def test_time_now_hcm():
    data = json.loads(time_now("Asia/Ho_Chi_Minh"))
    show_tool_result("time_now(Asia/Ho_Chi_Minh)", data)
    assert "error" not in data
    assert "date" in data["now"]
    assert "date_dmy" in data["now"]
    tz = str(data["now"]["timezone"])
    assert ("Ho_Chi_Minh" in tz) or tz in {"UTC+07:00", "+07:00"}


def test_time_shift_minus_7_days():
    data = json.loads(time_shift(datetime_str="2024-01-15", days=-7, timezone="UTC"))
    show_tool_result("time_shift(-7d)", data)
    assert data["result"]["date"] == "2024-01-08"
    assert data["result"]["date_dmy"] == "08-01-2024"


def test_time_convert_utc_to_hcm():
    data = json.loads(
        time_convert(
            "2024-01-15T00:00:00+00:00",
            from_timezone="UTC",
            to_timezone="Asia/Ho_Chi_Minh",
        )
    )
    show_tool_result("time_convert(UTC->HCM)", data)
    assert data["to"]["iso"].startswith("2024-01-15T07:00:00")
