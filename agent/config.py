"""Knob agent đọc từ env (.env). Sửa tại đây / .env, không hardcode trong node.

Env:
  MAX_REVIEW_LOOPS           mặc định 2
  JEV_CONFIDENCE_THRESHOLD   mặc định 0.65
  TOOL_SELECT_MAX_RETRIES    mặc định 1 (retry khi tool_select tên trống/không hợp lệ)
  PLANNER_MAX_RETRIES        mặc định 1 (số lần sửa mỗi bước lỗi args/tên/$stepN lúc execute)
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

DEFAULT_MAX_REVIEW_LOOPS = 2
DEFAULT_JEV_CONFIDENCE_THRESHOLD = 0.65
DEFAULT_TOOL_SELECT_MAX_RETRIES = 1
DEFAULT_PLANNER_MAX_RETRIES = 1


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid {name}={raw!r}; expected int.") from exc


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid {name}={raw!r}; expected float.") from exc


def get_max_review_loops() -> int:
    return _env_int("MAX_REVIEW_LOOPS", DEFAULT_MAX_REVIEW_LOOPS)


def get_jev_confidence_threshold() -> float:
    return _env_float("JEV_CONFIDENCE_THRESHOLD", DEFAULT_JEV_CONFIDENCE_THRESHOLD)


def get_tool_select_max_retries() -> int:
    """Số lần retry sau lần chọn tool đầu (tên trống hoặc không hợp lệ). Tối thiểu 0."""
    return max(0, _env_int("TOOL_SELECT_MAX_RETRIES", DEFAULT_TOOL_SELECT_MAX_RETRIES))


def get_planner_max_retries() -> int:
    """Số lần sửa mỗi bước lỗi (tên/args/$stepN) trong plan_execution. Tối thiểu 0."""
    return max(0, _env_int("PLANNER_MAX_RETRIES", DEFAULT_PLANNER_MAX_RETRIES))


__all__ = [
    "DEFAULT_MAX_REVIEW_LOOPS",
    "DEFAULT_JEV_CONFIDENCE_THRESHOLD",
    "DEFAULT_TOOL_SELECT_MAX_RETRIES",
    "DEFAULT_PLANNER_MAX_RETRIES",
    "get_max_review_loops",
    "get_jev_confidence_threshold",
    "get_tool_select_max_retries",
    "get_planner_max_retries",
]
