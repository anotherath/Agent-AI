"""Pytest bootstrap: load .env và thêm project root vào sys.path."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")


def show_tool_result(label: str, payload: Any) -> None:
    """In kết quả tool ra terminal khi chạy pytest -s."""
    print("\n" + "=" * 72)
    print(f"[TOOL RESULT] {label}")
    print("=" * 72)
    if isinstance(payload, (dict, list)):
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    else:
        text = str(payload)
        # Tránh dump quá dài trên terminal
        if len(text) > 4000:
            print(text[:4000] + "\n... [truncated]")
        else:
            print(text)
    print("=" * 72 + "\n")
