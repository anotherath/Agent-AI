"""TypeSafe Jev Choice client (optional — thiếu key / SDK → None)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class JevChoiceResult:
    choice: str
    confidence: float
    probabilities: dict[str, float]


def jev_available() -> bool:
    if not os.getenv("TYPESAFE_API_KEY", "").strip():
        return False
    try:
        import typesafe_sdk  # noqa: F401
    except ImportError:
        return False
    return True


def classify_choice(
    *,
    state: str | Mapping[str, object],
    question_id: str,
    instructions: str,
    criteria: Mapping[str, str],
) -> JevChoiceResult | None:
    """Gọi Jev Choice. Trả None nếu chưa cấu hình / lỗi — caller fallback LLM."""
    if not jev_available():
        return None

    from typesafe_sdk import Choice, TypeSafeClient

    try:
        with TypeSafeClient() as client:
            response = client.system_one(
                state=state,
                questions={
                    question_id: Choice(
                        instructions=instructions,
                        criteria=dict(criteria),
                    ),
                },
            )
        answer = response.choices[question_id]
        probs = {
            str(k): float(v) for k, v in (answer.probabilities or {}).items()
        }
        return JevChoiceResult(
            choice=str(answer.choice),
            confidence=float(answer.confidence),
            probabilities=probs,
        )
    except Exception:  # noqa: BLE001 — port: mọi lỗi → LLM fallback
        return None


__all__ = ["JevChoiceResult", "classify_choice", "jev_available"]
