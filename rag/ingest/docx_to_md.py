"""DOCX → Markdown (MVP: heading + paragraph + bảng đơn giản)."""

from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

from rag.ingest.types import (
    SourceType,
    ToMarkdownError,
    ToMarkdownResult,
    resolve_existing_file,
    write_markdown_output,
)

_HEADING_RE = re.compile(r"^heading\s+(\d+)$", re.IGNORECASE)


def _paragraph_to_md(paragraph: Paragraph) -> str | None:
    text = (paragraph.text or "").strip()
    if not text:
        return None

    style_name = (paragraph.style.name if paragraph.style else "") or ""
    match = _HEADING_RE.match(style_name.strip())
    if match:
        level = min(max(int(match.group(1)), 1), 6)
        return f"{'#' * level} {text}"
    return text


def _table_to_md(table: Table) -> str:
    rows: list[list[str]] = []
    for row in table.rows:
        cells = [" ".join(cell.text.split()) for cell in row.cells]
        rows.append(cells)
    if not rows:
        return ""

    width = max(len(r) for r in rows)
    normalized = [r + [""] * (width - len(r)) for r in rows]
    header = normalized[0]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for row in normalized[1:]:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _docx_body_to_markdown(doc: Document) -> str:
    blocks: list[str] = []
    for block in doc.element.body:
        tag = block.tag.split("}")[-1]
        if tag == "p":
            line = _paragraph_to_md(Paragraph(block, doc))
            if line:
                blocks.append(line)
        elif tag == "tbl":
            md = _table_to_md(Table(block, doc))
            if md:
                blocks.append(md)
    return "\n\n".join(blocks).strip() + ("\n" if blocks else "")


def docx_to_markdown(
    path: str | Path,
    *,
    output_path: str | Path | None = None,
) -> ToMarkdownResult:
    """Chuyển DOCX sang Markdown."""
    src = resolve_existing_file(path)
    if src.suffix.lower() != ".docx":
        raise ToMarkdownError(f"Không phải DOCX: {src}")

    try:
        doc = Document(str(src))
        markdown = _docx_body_to_markdown(doc)
    except ToMarkdownError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise ToMarkdownError(str(exc)) from exc

    written = write_markdown_output(markdown, output_path) if output_path is not None else None
    return ToMarkdownResult(
        source_path=src,
        source_type=SourceType.DOCX,
        markdown=markdown,
        output_path=written,
    )


__all__ = ["docx_to_markdown"]
