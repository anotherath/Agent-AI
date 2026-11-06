"""PDF → Markdown via pymupdf4llm (text layer only, no OCR).

Shared helper for ingest pipeline, services, workers, and agent tools.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pymupdf4llm


class PdfToMarkdownError(ValueError):
    """Invalid input or conversion failure for PDF → Markdown."""


@dataclass(frozen=True, slots=True)
class PdfToMarkdownResult:
    """Kết quả chuyển PDF sang Markdown."""

    pdf_path: Path
    markdown: str
    pages: list[int] | None
    output_path: Path | None = None

    @property
    def char_count(self) -> int:
        return len(self.markdown)


def _resolve_pdf(pdf_path: str | Path) -> Path:
    src = Path(pdf_path).expanduser().resolve()
    if not src.is_file():
        raise PdfToMarkdownError(f"File không tồn tại: {src}")
    if src.suffix.lower() != ".pdf":
        raise PdfToMarkdownError(f"Không phải PDF: {src}")
    return src


def pdf_to_markdown(
    pdf_path: str | Path,
    *,
    output_path: str | Path | None = None,
    pages: list[int] | None = None,
) -> PdfToMarkdownResult:
    """Chuyển PDF (có text layer) sang Markdown.

    Args:
        pdf_path: Đường dẫn file PDF local.
        output_path: Nếu set, ghi Markdown ra file (.md) và trả path trong result.
        pages: Danh sách trang 0-based; ``None`` = mọi trang.

    Raises:
        PdfToMarkdownError: File thiếu / không phải PDF / lỗi convert.
    """
    src = _resolve_pdf(pdf_path)

    kwargs: dict = {
        "doc": str(src),
        "use_ocr": False,
        "force_ocr": False,
    }
    if pages is not None:
        kwargs["pages"] = pages

    try:
        markdown = pymupdf4llm.to_markdown(**kwargs)
    except Exception as exc:  # noqa: BLE001 - normalize cho caller
        raise PdfToMarkdownError(str(exc)) from exc

    if not isinstance(markdown, str):
        markdown = str(markdown)

    written: Path | None = None
    if output_path is not None:
        dest = Path(output_path).expanduser().resolve()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(markdown, encoding="utf-8")
        written = dest

    return PdfToMarkdownResult(
        pdf_path=src,
        markdown=markdown,
        pages=pages,
        output_path=written,
    )


__all__ = [
    "PdfToMarkdownError",
    "PdfToMarkdownResult",
    "pdf_to_markdown",
]
