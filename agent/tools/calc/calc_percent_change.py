"""Tool: calc_percent_change — phần trăm thay đổi."""

from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from agent.tools.calc.descriptions import (
    CALC_PERCENT_CHANGE,
    CALC_PERCENT_CHANGE_NEW,
    CALC_PERCENT_CHANGE_OLD,
)
from agent.tools.calc.safe import to_tool_result


class PercentChangeInput(BaseModel):
    old: float = Field(description=CALC_PERCENT_CHANGE_OLD)
    new: float = Field(description=CALC_PERCENT_CHANGE_NEW)


def calc_percent_change(old: float, new: float) -> str:
    """Tính ((new - old) / old) * 100."""
    try:
        if old == 0:
            return to_tool_result(
                {"error": "old=0 không chia được để tính phần trăm thay đổi"}
            )
        change = new - old
        percent = (change / old) * 100
        return to_tool_result(
            {
                "old": old,
                "new": new,
                "absolute_change": change,
                "percent_change": percent,
            }
        )
    except Exception as exc:  # noqa: BLE001
        return to_tool_result({"error": str(exc)})


def get_calc_percent_change_tool() -> StructuredTool:
    return StructuredTool.from_function(
        name="calc_percent_change",
        description=CALC_PERCENT_CHANGE,
        func=calc_percent_change,
        args_schema=PercentChangeInput,
    )
