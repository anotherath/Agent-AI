"""Kiểu dùng chung cho ingest (source types, to-markdown)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class SourceType(StrEnum):
    """Định dạng nguồn MVP — khớp ingest-pipeline.md."""

    PDF = "pdf"
    MARKDOWN = "markdown"
    TEXT = "text"
    DOCX = "docx"


class ToMarkdownError(ValueError):
    """Lỗi convert / load sang Markdown."""


@dataclass(frozen=True, slots=True)
class ToMarkdownResult:
    """Kết quả stage To Markdown (mọi source_type)."""

    source_path: Path
    source_type: SourceType
    markdown: str
    output_path: Path | None = None
    pages: list[int] | None = None  # chỉ PDF

    @property
    def char_count(self) -> int:
        return len(self.markdown)


_EXT_TO_SOURCE: dict[str, SourceType] = {
    ".pdf": SourceType.PDF,
    ".md": SourceType.MARKDOWN,
    ".markdown": SourceType.MARKDOWN,
    ".txt": SourceType.TEXT,
    ".docx": SourceType.DOCX,
}


def resolve_source_type(
    path: Path,
    source_type: SourceType | str | None = None,
) -> SourceType:
    """Suy ``source_type`` từ arg hoặc extension."""
    if source_type is not None:
        try:
            return SourceType(str(source_type).strip().lower())
        except ValueError as exc:
            raise ToMarkdownError(
                f"source_type không hỗ trợ: {source_type!r}. "
                f"MVP: {[s.value for s in SourceType]}"
            ) from exc

    ext = path.suffix.lower()
    if ext not in _EXT_TO_SOURCE:
        raise ToMarkdownError(
            f"Không suy được source_type từ extension {ext!r}. "
            "Truyền source_type hoặc dùng .pdf/.md/.txt/.docx"
        )
    return _EXT_TO_SOURCE[ext]


def resolve_existing_file(path: str | Path) -> Path:
    src = Path(path).expanduser().resolve()
    if not src.is_file():
        raise ToMarkdownError(f"File không tồn tại: {src}")
    return src


def write_markdown_output(markdown: str, output_path: str | Path) -> Path:
    dest = Path(output_path).expanduser().resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(markdown, encoding="utf-8")
    return dest


__all__ = [
    "SourceType",
    "ToMarkdownError",
    "ToMarkdownResult",
    "resolve_source_type",
    "resolve_existing_file",
    "write_markdown_output",
]
