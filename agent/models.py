"""Factory ChatOpenAI dùng chung (generate, planner, LLM fallback).

Env (legacy / chung):
  OPENAI_TEMPERATURE, OPENAI_REASONING_MAX_TOKENS, OPENAI_GENERATE_MAX_TOKENS,
  OPENAI_TOP_P / OPENAI_TOP_K

Provider/model/key: xem agent/llm_providers.py + config/llm_providers.yaml
(LLM_PROVIDERS_FILE). Fallback OPENAI_API_KEY + OPENAI_BASE_URL + OPENAI_MODEL
khi chưa có YAML.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from contextvars import ContextVar
from functools import lru_cache
from typing import Iterator

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from agent.llm_providers import resolve_model

load_dotenv()

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TEMPERATURE = 0.0
DEFAULT_REASONING_MAX_TOKENS = 1024
DEFAULT_GENERATE_MAX_TOKENS = 2048

# Model catalog id cho toàn bộ LLM calls trong một agent run.
_llm_model_ctx: ContextVar[str | None] = ContextVar("llm_catalog_model", default=None)


@contextmanager
def llm_model_scope(model: str | None) -> Iterator[None]:
    """Gắn catalog model cho get_chat_model() trong scope (một chat turn).

    Khôi phục bằng set(previous), không dùng reset(token): scope hay bọc
    async for / LangGraph copy_context — reset token ở Context khác sẽ lỗi
    \"Token was created in a different Context\".
    """
    previous = _llm_model_ctx.get()
    _llm_model_ctx.set((model or "").strip() or None)
    try:
        yield
    finally:
        _llm_model_ctx.set(previous)


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


@lru_cache(maxsize=32)
def _cached_chat_model(
    *,
    catalog_id: str,
    credential_id: str,
    upstream_model: str,
    base_url: str,
    api_key: str,
    temperature: float,
    max_tokens: int,
    top_p: float | None,
    top_k: int | None,
) -> ChatOpenAI:
    kwargs: dict = {
        "model": upstream_model,
        "api_key": api_key,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if base_url:
        kwargs["base_url"] = base_url
    if top_p is not None:
        kwargs["top_p"] = top_p
    if top_k is not None:
        kwargs["model_kwargs"] = {"top_k": top_k}
    # catalog_id / credential_id chỉ để phân biệt cache key.
    _ = (catalog_id, credential_id)
    return ChatOpenAI(**kwargs)


def get_chat_model(
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    top_p: float | None = None,
    top_k: int | None = None,
) -> ChatOpenAI:
    """Tạo (và cache) ChatOpenAI theo catalog / override.

    model: catalog id (`provider:name`). None → scope hiện tại → default catalog.
    Không truyền max_tokens → dùng ngân sách reasoning.
    Node generate phải truyền resolve_generate_max_tokens().
    """
    catalog_id = (model or "").strip() or _llm_model_ctx.get()
    resolved = resolve_model(catalog_id)
    return _cached_chat_model(
        catalog_id=resolved.catalog_id,
        credential_id=resolved.credential_id,
        upstream_model=resolved.upstream_model,
        base_url=resolved.base_url or "",
        api_key=resolved.api_key,
        temperature=_temperature(temperature),
        max_tokens=(
            max_tokens if max_tokens is not None else resolve_reasoning_max_tokens()
        ),
        top_p=_optional_float("OPENAI_TOP_P", top_p),
        top_k=_optional_int("OPENAI_TOP_K", top_k),
    )


def clear_chat_model_cache() -> None:
    """Xóa cache (test / đổi env runtime)."""
    _cached_chat_model.cache_clear()


__all__ = [
    "get_chat_model",
    "clear_chat_model_cache",
    "llm_model_scope",
    "resolve_reasoning_max_tokens",
    "resolve_generate_max_tokens",
    "DEFAULT_MODEL",
    "DEFAULT_REASONING_MAX_TOKENS",
    "DEFAULT_GENERATE_MAX_TOKENS",
]
