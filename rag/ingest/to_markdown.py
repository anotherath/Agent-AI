"""Stage To Markdown — dispatcher theo ``source_type`` (ingest-pipeline §3)."""

from __future__ import annotations

from pathlib import Path

from rag.ingest.docx_to_md import docx_to_markdown
from rag.ingest.load_text import load_text_file
from rag.ingest.pdf_to_md import PdfToMarkdownError, pdf_to_markdown
from rag.ingest.types import (
    SourceType,
    ToMarkdownError,
    ToMarkdownResult,
    resolve_existing_file,
    resolve_source_type,
)


def to_markdown(
    path: str | Path,
    *,
    source_type: SourceType | str | None = None,
    output_path: str | Path | None = None,
    pages: list[int] | None = None,
) -> ToMarkdownResult:
    """Đưa file nguồn về Markdown theo ``source_type``.

    - ``pdf``: pymupdf4llm (text layer; ``pages`` 0-based optional)
    - ``markdown`` / ``text``: đọc UTF-8, không convert
    - ``docx``: DOCX → Markdown

    ``source_type=None`` → suy từ extension.
    """
    src = resolve_existing_file(path)
    kind = resolve_source_type(src, source_type)

    if pages is not None and kind is not SourceType.PDF:
        raise ToMarkdownError("pages chỉ dùng với source_type=pdf")

    if kind is SourceType.PDF:
        try:
            pdf_result = pdf_to_markdown(src, output_path=output_path, pages=pages)
        except PdfToMarkdownError as exc:
            raise ToMarkdownError(str(exc)) from exc
        return ToMarkdownResult(
            source_path=pdf_result.pdf_path,
            source_type=SourceType.PDF,
            markdown=pdf_result.markdown,
            output_path=pdf_result.output_path,
            pages=pdf_result.pages,
        )

    if kind in {SourceType.MARKDOWN, SourceType.TEXT}:
        return load_text_file(src, source_type=kind, output_path=output_path)

    if kind is SourceType.DOCX:
        return docx_to_markdown(src, output_path=output_path)

    raise ToMarkdownError(f"source_type chưa hỗ trợ: {kind}")


__all__ = ["to_markdown"]
