"""Chat model factory (OpenAI-compatible via langchain-openai).

Env:
  OPENAI_API_KEY   — bắt buộc
  OPENAI_MODEL     — mặc định gpt-4o-mini
  OPENAI_BASE_URL  — optional (mặc định API OpenAI; set nếu dùng provider tương thích)
  OPENAI_TEMPERATURE — mặc định 0.0
  OPENAI_TOP_P     — optional (nucleus sampling; bỏ trống = không gửi)
  OPENAI_TOP_K     — optional (qua model_kwargs; OpenAI official thường không dùng,
                     hữu ích với provider tương thích)
"""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TEMPERATURE = 0.0


def _require_api_key() -> str:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise ValueError(
            "Missing OPENAI_API_KEY. Set it in the environment or .env file."
        )
    return key


def _model_name() -> str:
    return os.getenv("OPENAI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


def _parse_float(name: str, raw: str) -> float:
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid {name}={raw!r}; expected a float.") from exc


def _parse_int(name: str, raw: str) -> int:
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid {name}={raw!r}; expected an int.") from exc


def _temperature(override: float | None) -> float:
    if override is not None:
        return override
    raw = os.getenv("OPENAI_TEMPERATURE", str(DEFAULT_TEMPERATURE)).strip()
    return _parse_float("OPENAI_TEMPERATURE", raw)


def _optional_float(name: str, override: float | None) -> float | None:
    if override is not None:
        return override
    raw = os.getenv(name, "").strip()
    if not raw:
        return None
    return _parse_float(name, raw)


def _optional_int(name: str, override: int | None) -> int | None:
    if override is not None:
        return override
    raw = os.getenv(name, "").strip()
    if not raw:
        return None
    return _parse_int(name, raw)


def _base_url() -> str | None:
    url = os.getenv("OPENAI_BASE_URL", "").strip()
    return url or None


@lru_cache(maxsize=16)
def get_chat_model(
    *,
    model: str | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
    top_k: int | None = None,
) -> ChatOpenAI:
    """Trả về ChatOpenAI dùng chung cho nodes (generate, planner, LLM fallback)."""
    kwargs: dict = {
        "model": model or _model_name(),
        "api_key": _require_api_key(),
        "temperature": _temperature(temperature),
    }
    base_url = _base_url()
    if base_url:
        kwargs["base_url"] = base_url

    resolved_top_p = _optional_float("OPENAI_TOP_P", top_p)
    if resolved_top_p is not None:
        kwargs["top_p"] = resolved_top_p

    resolved_top_k = _optional_int("OPENAI_TOP_K", top_k)
    if resolved_top_k is not None:
        kwargs["model_kwargs"] = {"top_k": resolved_top_k}

    return ChatOpenAI(**kwargs)


def clear_chat_model_cache() -> None:
    """Xóa cache factory (dùng khi đổi env trong test)."""
    get_chat_model.cache_clear()


__all__ = ["get_chat_model", "clear_chat_model_cache", "DEFAULT_MODEL"]
