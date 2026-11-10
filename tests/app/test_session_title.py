"""Unit tests for auto session title helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.session_title import (
    fallback_title,
    generate_session_title,
    sanitize_title,
    should_autotitle,
)


def test_should_autotitle_only_first_empty_main() -> None:
    main_empty = SimpleNamespace(is_main=True, title=None)
    main_titled = SimpleNamespace(is_main=True, title="Đã có tên")
    sub = SimpleNamespace(is_main=False, title=None)

    assert should_autotitle(main_empty, message_count=1) is True
    assert should_autotitle(main_empty, message_count=2) is False
    assert should_autotitle(main_titled, message_count=1) is False
    assert should_autotitle(sub, message_count=1) is False


def test_sanitize_and_fallback() -> None:
    assert sanitize_title('"API login JWT."', fallback_source="x") == "API login JWT"
    assert fallback_title("a" * 80).startswith("a")
    assert len(fallback_title("a" * 80)) <= 50
    assert fallback_title("") == "Cuộc trò chuyện mới"


def test_generate_session_title_uses_llm_then_sanitize() -> None:
    fake_resp = SimpleNamespace(content='  "Giải thích RAG"  ')
    fake_llm = MagicMock()
    fake_llm.invoke.return_value = fake_resp

    with patch(
        "agent.models.get_chat_model",
        return_value=fake_llm,
    ):
        title = generate_session_title("Giải thích cơ chế RAG cho người mới")

    assert title == "Giải thích RAG"
    fake_llm.invoke.assert_called_once()
    messages = fake_llm.invoke.call_args.args[0]
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    content = messages[0]["content"]
    assert "Giải thích cơ chế RAG cho người mới" in content
    assert "Đặt tiêu đề ngắn" in content
    assert "CẤM trả lời" in content


def test_generate_session_title_fallback_on_llm_error() -> None:
    with patch(
        "agent.models.get_chat_model",
        side_effect=RuntimeError("boom"),
    ):
        title = generate_session_title("Viết giúp tôi một API login bằng JWT")

    assert "API" in title or "login" in title or "JWT" in title
