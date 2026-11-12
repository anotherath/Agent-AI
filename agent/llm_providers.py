"""Catalog LLM: provider → credential (api_key_env) → models.

Env:
  LLM_PROVIDERS_FILE   path YAML (mặc định config/llm_providers.yaml từ repo root)
Nếu file thiếu / lỗi → fallback legacy OPENAI_API_KEY + OPENAI_BASE_URL + OPENAI_MODEL.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

load_dotenv()

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_PROVIDERS_FILE = _REPO_ROOT / "config" / "llm_providers.yaml"
_LEGACY_PROVIDER_ID = "default"
_LEGACY_PROVIDER_LABEL = "Default"


@dataclass(frozen=True)
class PublicModel:
    """Model FE được list (không có secret)."""

    id: str
    provider: str
    provider_label: str
    label: str
    is_default: bool


@dataclass(frozen=True)
class ResolvedModel:
    """Thông tin runtime để tạo ChatOpenAI."""

    catalog_id: str
    provider_id: str
    provider_label: str
    credential_id: str
    upstream_model: str
    label: str
    base_url: str | None
    api_key: str


@dataclass(frozen=True)
class _ModelEntry:
    provider_id: str
    provider_label: str
    base_url: str | None
    credential_id: str
    api_key_env: str
    upstream_model: str
    label: str


@dataclass(frozen=True)
class _Catalog:
    default_id: str
    by_id: dict[str, _ModelEntry]
    public: tuple[PublicModel, ...]


class UnknownModelError(ValueError):
    """Catalog id không nằm trong allowlist."""


def _providers_file() -> Path:
    raw = os.getenv("LLM_PROVIDERS_FILE", "").strip()
    if not raw:
        return _DEFAULT_PROVIDERS_FILE
    path = Path(raw)
    if not path.is_absolute():
        path = _REPO_ROOT / path
    return path


def _catalog_id(provider_id: str, model_id: str) -> str:
    return f"{provider_id}:{model_id}"


def _require_str(data: dict[str, Any], key: str, *, ctx: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{ctx}: missing/invalid {key!r}")
    return value.strip()


def _optional_str(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"invalid {key!r}")
    text = value.strip()
    return text or None


def _load_yaml_catalog(path: Path) -> _Catalog:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: root must be a mapping")

    providers = raw.get("providers")
    if not isinstance(providers, dict) or not providers:
        raise ValueError(f"{path}: providers must be a non-empty mapping")

    by_id: dict[str, _ModelEntry] = {}
    public_rows: list[tuple[str, PublicModel]] = []

    for provider_id, pdata in providers.items():
        if not isinstance(provider_id, str) or not provider_id.strip():
            raise ValueError(f"{path}: invalid provider id")
        provider_id = provider_id.strip()
        if not isinstance(pdata, dict):
            raise ValueError(f"{path}: provider {provider_id!r} must be a mapping")

        provider_label = _optional_str(pdata, "label") or provider_id
        base_url = _optional_str(pdata, "base_url")
        credentials = pdata.get("credentials")
        if not isinstance(credentials, list) or not credentials:
            raise ValueError(
                f"{path}: provider {provider_id!r} needs non-empty credentials"
            )

        for cred in credentials:
            if not isinstance(cred, dict):
                raise ValueError(f"{path}: credential must be a mapping")
            cred_id = _require_str(cred, "id", ctx=f"provider {provider_id}")
            api_key_env = _require_str(
                cred, "api_key_env", ctx=f"credential {provider_id}/{cred_id}"
            )
            models = cred.get("models")
            if not isinstance(models, list) or not models:
                raise ValueError(
                    f"{path}: credential {provider_id}/{cred_id} needs models"
                )
            for m in models:
                if not isinstance(m, dict):
                    raise ValueError(f"{path}: model entry must be a mapping")
                mid = _require_str(
                    m, "id", ctx=f"model under {provider_id}/{cred_id}"
                )
                label = _optional_str(m, "label") or mid
                cid = _catalog_id(provider_id, mid)
                if cid in by_id:
                    # Credential đầu tiên thắng (FE không chọn key).
                    continue
                by_id[cid] = _ModelEntry(
                    provider_id=provider_id,
                    provider_label=provider_label,
                    base_url=base_url,
                    credential_id=cred_id,
                    api_key_env=api_key_env,
                    upstream_model=mid,
                    label=label,
                )
                public_rows.append(
                    (
                        cid,
                        PublicModel(
                            id=cid,
                            provider=provider_id,
                            provider_label=provider_label,
                            label=label,
                            is_default=False,
                        ),
                    )
                )

    if not by_id:
        raise ValueError(f"{path}: no models defined")

    default_raw = _optional_str(raw, "default_model")
    if default_raw:
        if default_raw not in by_id:
            raise ValueError(
                f"{path}: default_model={default_raw!r} not in catalog"
            )
        default_id = default_raw
    else:
        default_id = next(iter(by_id))

    public = tuple(
        PublicModel(
            id=pm.id,
            provider=pm.provider,
            provider_label=pm.provider_label,
            label=pm.label,
            is_default=(pm.id == default_id),
        )
        for _, pm in public_rows
    )
    return _Catalog(default_id=default_id, by_id=by_id, public=public)


def _legacy_catalog() -> _Catalog:
    """Một provider ảo từ OPENAI_* khi chưa có YAML."""
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    base_url = os.getenv("OPENAI_BASE_URL", "").strip() or None
    cid = _catalog_id(_LEGACY_PROVIDER_ID, model)
    entry = _ModelEntry(
        provider_id=_LEGACY_PROVIDER_ID,
        provider_label=_LEGACY_PROVIDER_LABEL,
        base_url=base_url,
        credential_id="main",
        api_key_env="OPENAI_API_KEY",
        upstream_model=model,
        label=model,
    )
    public = (
        PublicModel(
            id=cid,
            provider=_LEGACY_PROVIDER_ID,
            provider_label=_LEGACY_PROVIDER_LABEL,
            label=model,
            is_default=True,
        ),
    )
    return _Catalog(default_id=cid, by_id={cid: entry}, public=public)


@lru_cache(maxsize=1)
def _get_catalog() -> _Catalog:
    path = _providers_file()
    if path.is_file():
        return _load_yaml_catalog(path)
    return _legacy_catalog()


def clear_llm_providers_cache() -> None:
    """Test / reload YAML runtime."""
    _get_catalog.cache_clear()


def list_public_models() -> list[PublicModel]:
    return list(_get_catalog().public)


def default_model_id() -> str:
    return _get_catalog().default_id


def is_known_model(catalog_id: str | None) -> bool:
    if not catalog_id or not catalog_id.strip():
        return False
    return catalog_id.strip() in _get_catalog().by_id


def resolve_model(catalog_id: str | None = None) -> ResolvedModel:
    """Map catalog id → api_key + base_url + upstream model.

    None / rỗng → default_model. Id lạ → UnknownModelError.
    """
    catalog = _get_catalog()
    raw = (catalog_id or "").strip()
    cid = raw or catalog.default_id
    entry = catalog.by_id.get(cid)
    if entry is None:
        raise UnknownModelError(f"Unknown model: {cid!r}")

    api_key = os.getenv(entry.api_key_env, "").strip()
    if not api_key:
        raise ValueError(
            f"Missing {entry.api_key_env} for model {cid!r} "
            f"(credential {entry.provider_id}/{entry.credential_id})."
        )

    return ResolvedModel(
        catalog_id=cid,
        provider_id=entry.provider_id,
        provider_label=entry.provider_label,
        credential_id=entry.credential_id,
        upstream_model=entry.upstream_model,
        label=entry.label,
        base_url=entry.base_url,
        api_key=api_key,
    )


__all__ = [
    "PublicModel",
    "ResolvedModel",
    "UnknownModelError",
    "list_public_models",
    "default_model_id",
    "is_known_model",
    "resolve_model",
    "clear_llm_providers_cache",
]
