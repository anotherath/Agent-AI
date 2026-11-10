"""Auto-generate chat session titles (ChatGPT / Grok style)."""

from __future__ import annotations

import re

from app.db.models import ChatSession

_TITLE_MAX_CHARS = 80
_FALLBACK_MAX_CHARS = 50

_TITLE_PROMPT = (
    "Đặt tiêu đề ngắn cho tin nhắn chat bên dưới.\n"
    "Quy tắc:\n"
    "- 4 đến 8 từ, cùng ngôn ngữ với tin nhắn.\n"
    "- Không dấu ngoặc kép, không markdown, không emoji.\n"
    "- Không kết thúc bằng dấu chấm.\n"
    "- Chỉ trả về đúng một dòng tiêu đề.\n"
    "- CẤM trả lời / giải thích / từ chối nội dung — chỉ đặt tên.\n"
    "\n"
    "Tin nhắn:\n"
    '"""\n'
    "{message}\n"
    '"""'
)


def should_autotitle(session: ChatSession, *, message_count: int) -> bool:
    """Chỉ main session, title trống, và đúng tin nhắn đầu tiên."""
    if not session.is_main:
        return False
    if session.title and session.title.strip():
        return False
    return message_count == 1


def fallback_title(first_message: str) -> str:
    text = " ".join((first_message or "").split()).strip()
    if not text:
        return "Cuộc trò chuyện mới"
    if len(text) <= _FALLBACK_MAX_CHARS:
        return text
    cut = text[:_FALLBACK_MAX_CHARS].rsplit(" ", 1)[0].strip()
    return cut or text[:_FALLBACK_MAX_CHARS]


def sanitize_title(raw: str, *, fallback_source: str) -> str:
    text = (raw or "").strip()
    if not text:
        return fallback_title(fallback_source)
    # Chỉ lấy dòng đầu nếu model trả thêm giải thích
    text = text.splitlines()[0].strip()
    text = text.strip(" \"'`“”‘’")
    text = re.sub(r"[*_`#]+", "", text)
    text = " ".join(text.split()).strip(" .")
    if not text:
        return fallback_title(fallback_source)
    if len(text) > _TITLE_MAX_CHARS:
        text = (
            text[:_TITLE_MAX_CHARS].rsplit(" ", 1)[0].strip() or text[:_TITLE_MAX_CHARS]
        )
    return text


def generate_session_title(first_message: str) -> str:
    """Gọi LLM để sinh title; lỗi → fallback cắt tin nhắn đầu."""
    source = (first_message or "").strip()
    if not source:
        return fallback_title(source)

    try:
        from agent.models import get_chat_model

        llm = get_chat_model(temperature=0.2)
        resp = llm.invoke(
            [
                {
                    "role": "user",
                    "content": _TITLE_PROMPT.format(message=source),
                },
            ]
        )
        content = getattr(resp, "content", resp)
        if isinstance(content, list):
            content = "".join(
                (b.get("text") if isinstance(b, dict) else str(b)) for b in content
            )
        return sanitize_title(str(content), fallback_source=source)
    except Exception:  # noqa: BLE001 — title không được làm hỏng chat turn
        return fallback_title(source)


__all__ = [
    "should_autotitle",
    "fallback_title",
    "sanitize_title",
    "generate_session_title",
]
