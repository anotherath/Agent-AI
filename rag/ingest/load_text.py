"""Load ``.md`` / ``.txt`` UTF-8 → text/Markdown (không convert)."""

from __future__ import annotations

from pathlib import Path

from rag.ingest.types import (
    SourceType,
    ToMarkdownError,
    ToMarkdownResult,
    resolve_existing_file,
    write_markdown_output,
)


def _read_utf8(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ToMarkdownError(f"Không đọc được UTF-8: {path}") from exc


def load_text_file(
    path: str | Path,
    *,
    source_type: SourceType,
    output_path: str | Path | None = None,
) -> ToMarkdownResult:
    """Đọc file text/markdown sẵn — skip convert."""
    if source_type not in {SourceType.MARKDOWN, SourceType.TEXT}:
        raise ToMarkdownError(
            f"load_text_file chỉ nhận markdown|text, được: {source_type}"
        )

    src = resolve_existing_file(path)
    expected = {SourceType.MARKDOWN: {".md", ".markdown"}, SourceType.TEXT: {".txt"}}
    if src.suffix.lower() not in expected[source_type]:
        raise ToMarkdownError(
            f"Extension {src.suffix!r} không khớp source_type={source_type.value}"
        )

    text = _read_utf8(src)
    written = write_markdown_output(text, output_path) if output_path is not None else None
    return ToMarkdownResult(
        source_path=src,
        source_type=source_type,
        markdown=text,
        output_path=written,
    )


__all__ = ["load_text_file"]
