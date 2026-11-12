"""Unit tests cho catalog LLM providers."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent import llm_providers as lp
from agent.llm_providers import UnknownModelError


@pytest.fixture(autouse=True)
def _clear_catalog_cache():
    lp.clear_llm_providers_cache()
    yield
    lp.clear_llm_providers_cache()


def test_load_yaml_catalog(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    yaml_path = tmp_path / "providers.yaml"
    yaml_path.write_text(
        """
default_model: a:m1
providers:
  a:
    label: Alpha
    base_url: https://a.example/v1
    credentials:
      - id: main
        api_key_env: KEY_A
        models:
          - id: m1
            label: Model One
          - id: m2
            label: Model Two
  b:
    label: Beta
    base_url: https://b.example/v1
    credentials:
      - id: main
        api_key_env: KEY_B
        models:
          - id: m1
            label: Beta One
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("LLM_PROVIDERS_FILE", str(yaml_path))
    monkeypatch.setenv("KEY_A", "sk-a")
    monkeypatch.setenv("KEY_B", "sk-b")

    public = lp.list_public_models()
    ids = {m.id for m in public}
    assert ids == {"a:m1", "a:m2", "b:m1"}
    assert lp.default_model_id() == "a:m1"
    assert any(m.is_default for m in public if m.id == "a:m1")

    resolved = lp.resolve_model("b:m1")
    assert resolved.upstream_model == "m1"
    assert resolved.base_url == "https://b.example/v1"
    assert resolved.api_key == "sk-b"
    assert resolved.provider_label == "Beta"

    defaulted = lp.resolve_model(None)
    assert defaulted.catalog_id == "a:m1"
    assert defaulted.api_key == "sk-a"

    with pytest.raises(UnknownModelError):
        lp.resolve_model("a:unknown")


def test_duplicate_model_first_credential_wins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    yaml_path = tmp_path / "providers.yaml"
    yaml_path.write_text(
        """
default_model: p:x
providers:
  p:
    label: P
    base_url: https://p.example/v1
    credentials:
      - id: first
        api_key_env: KEY_FIRST
        models:
          - id: x
            label: X
      - id: second
        api_key_env: KEY_SECOND
        models:
          - id: x
            label: X again
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("LLM_PROVIDERS_FILE", str(yaml_path))
    monkeypatch.setenv("KEY_FIRST", "sk-first")
    monkeypatch.setenv("KEY_SECOND", "sk-second")

    resolved = lp.resolve_model("p:x")
    assert resolved.credential_id == "first"
    assert resolved.api_key == "sk-first"
    assert len(lp.list_public_models()) == 1


def test_legacy_fallback_without_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing = tmp_path / "nope.yaml"
    monkeypatch.setenv("LLM_PROVIDERS_FILE", str(missing))
    monkeypatch.setenv("OPENAI_MODEL", "gpt-legacy")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://legacy.example/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-legacy")

    assert lp.default_model_id() == "default:gpt-legacy"
    resolved = lp.resolve_model(None)
    assert resolved.upstream_model == "gpt-legacy"
    assert resolved.base_url == "https://legacy.example/v1"
    assert resolved.api_key == "sk-legacy"
