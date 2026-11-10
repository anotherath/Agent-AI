"""Factory ChatOpenAI dùng chung (generate, multi_plan, LLM fallback).

Env:
  OPENAI_API_KEY        bắt buộc
  OPENAI_MODEL          mặc định gpt-4o-mini
  OPENAI_TEMPERATURE    mặc định 0.0
  OPENAI_BASE_URL       optional (proxy / OpenAI-compatible); trống = default SDK
  OPENAI_REASONING_MAX_TOKENS  ngân sách suy luận (route/plan/tool/title)
  OPENAI_MAX_TOKENS            alias cũ → fallback cho reasoning
  OPENAI_GENERATE_MAX_TOKENS   ngân sách câu trả lời cuối (node generate)
  OPENAI_TOP_P / OPENAI_TOP_K  optional
"""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TEMPERATURE = 0.0
DEFAULT_REASONING_MAX_TOKENS = 1024
DEFAULT_GENERATE_MAX_TOKENS = 2048


# --- Đọc env ---


def _require_api_key() -> str:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise ValueError(
            "Missing OPENAI_API_KEY. Set it in the environment or .env file."
        )
    return key


def _model_name() -> str:
    return os.getenv("OPENAI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


def _base_url() -> str | None:
    raw = os.getenv("OPENAI_BASE_URL", "").strip()
    return raw or None


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


def resolve_reasoning_max_tokens(override: int | None = None) -> int:
    """Ngân sách suy luận: route / plan / review / tool-LLM / title."""
    if override is not None:
        return override
    raw = os.getenv("OPENAI_REASONING_MAX_TOKENS", "").strip()
    if raw:
        return _parse_int("OPENAI_REASONING_MAX_TOKENS", raw)
    legacy = os.getenv("OPENAI_MAX_TOKENS", "").strip()
    if legacy:
        return _parse_int("OPENAI_MAX_TOKENS", legacy)
    return DEFAULT_REASONING_MAX_TOKENS


def resolve_generate_max_tokens(override: int | None = None) -> int:
    """Ngân sách câu trả lời cuối (node generate) — tách khỏi reasoning."""
    if override is not None:
        return override
    raw = os.getenv("OPENAI_GENERATE_MAX_TOKENS", "").strip()
    if raw:
        return _parse_int("OPENAI_GENERATE_MAX_TOKENS", raw)
    return DEFAULT_GENERATE_MAX_TOKENS


# --- Public API ---


@lru_cache(maxsize=16)
def get_chat_model(
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    top_p: float | None = None,
    top_k: int | None = None,
) -> ChatOpenAI:
    """Tạo (và cache) ChatOpenAI theo env / override.

    Không truyền max_tokens → dùng ngân sách reasoning.
    Node generate phải truyền resolve_generate_max_tokens().
    """
    kwargs: dict = {
        "model": model or _model_name(),
        "api_key": _require_api_key(),
        "temperature": _temperature(temperature),
        "max_tokens": (
            max_tokens
            if max_tokens is not None
            else resolve_reasoning_max_tokens()
        ),
    }

    base_url = _base_url()
    if base_url is not None:
        kwargs["base_url"] = base_url

    resolved_top_p = _optional_float("OPENAI_TOP_P", top_p)
    if resolved_top_p is not None:
        kwargs["top_p"] = resolved_top_p

    resolved_top_k = _optional_int("OPENAI_TOP_K", top_k)
    if resolved_top_k is not None:
        kwargs["model_kwargs"] = {"top_k": resolved_top_k}

    return ChatOpenAI(**kwargs)


def clear_chat_model_cache() -> None:
    """Xóa cache (test / đổi env runtime)."""
    get_chat_model.cache_clear()


__all__ = [
    "get_chat_model",
    "clear_chat_model_cache",
    "resolve_reasoning_max_tokens",
    "resolve_generate_max_tokens",
    "DEFAULT_MODEL",
    "DEFAULT_REASONING_MAX_TOKENS",
    "DEFAULT_GENERATE_MAX_TOKENS",
]
