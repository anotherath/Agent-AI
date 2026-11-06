"""Helpers thời gian dùng zoneinfo (stdlib)."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def to_tool_result(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def get_tz(name: str) -> ZoneInfo:
    key = (name or "UTC").strip()
    try:
        return ZoneInfo(key)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(
            f"Timezone không hợp lệ: '{name}'. "
            "Ví dụ: UTC, Asia/Ho_Chi_Minh, America/New_York"
        ) from exc


def parse_datetime(value: str, default_tz: str = "UTC") -> datetime:
    """
    Parse ISO-8601 hoặc yyyy-mm-dd / dd-mm-yyyy.
    Nếu naive → gắn default_tz.
    """
    text = value.strip()
    if not text:
        raise ValueError("Thời gian trống")

    # dd-mm-yyyy (CoinGecko style)
    m = re.fullmatch(r"(\d{2})-(\d{2})-(\d{4})", text)
    if m:
        day, month, year = map(int, m.groups())
        return datetime(year, month, day, tzinfo=get_tz(default_tz))

    # yyyy-mm-dd
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        year, month, day = map(int, m.groups())
        return datetime(year, month, day, tzinfo=get_tz(default_tz))

    normalized = text.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=get_tz(default_tz))
    return dt


def format_payload(dt: datetime) -> dict[str, Any]:
    dt_utc = dt.astimezone(UTC)
    return {
        "iso": dt.isoformat(),
        "iso_utc": dt_utc.isoformat(),
        "unix": int(dt.timestamp()),
        "timezone": str(dt.tzinfo),
        "coingecko_date": dt.strftime("%d-%m-%Y"),
        "date": dt.strftime("%Y-%m-%d"),
        "time": dt.strftime("%H:%M:%S"),
    }
