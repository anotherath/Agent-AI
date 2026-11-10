"""Unit tests dispatcher ``rag.ingest.to_markdown`` + loaders."""

from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest
from docx import Document

from rag.ingest import SourceType, ToMarkdownError, to_markdown


def _make_sample_pdf(path: Path) -> None:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Hello PDF to Markdown\n\nSection One")
    doc.save(path)
    doc.close()


def _make_sample_docx(path: Path) -> None:
    doc = Document()
    doc.add_heading("Doc Title", level=1)
    doc.add_paragraph("Hello from docx body.")
    doc.save(path)


def test_to_markdown_pdf(tmp_path: Path):
    pdf = tmp_path / "sample.pdf"
    _make_sample_pdf(pdf)
    result = to_markdown(pdf)
    assert result.source_type is SourceType.PDF
    assert result.char_count > 0
    assert "Hello" in result.markdown or "Section" in result.markdown


def test_to_markdown_md(tmp_path: Path):
    md = tmp_path / "note.md"
    md.write_text("# Title\n\nBody text\n", encoding="utf-8")
    result = to_markdown(md)
    assert result.source_type is SourceType.MARKDOWN
    assert result.markdown.startswith("# Title")


def test_to_markdown_txt_bom(tmp_path: Path):
    txt = tmp_path / "note.txt"
    txt.write_bytes(b"\xef\xbb\xbfplain text line\n")
    result = to_markdown(txt)
    assert result.source_type is SourceType.TEXT
    assert result.markdown.startswith("plain text")


def test_to_markdown_docx(tmp_path: Path):
    docx = tmp_path / "sample.docx"
    _make_sample_docx(docx)
    result = to_markdown(docx)
    assert result.source_type is SourceType.DOCX
    assert "Doc Title" in result.markdown
    assert "Hello from docx" in result.markdown
    assert "# Doc Title" in result.markdown


def test_to_markdown_explicit_source_type(tmp_path: Path):
    md = tmp_path / "note.md"
    md.write_text("hello", encoding="utf-8")
    result = to_markdown(md, source_type="markdown")
    assert result.source_type is SourceType.MARKDOWN


def test_to_markdown_write_output(tmp_path: Path):
    md = tmp_path / "note.md"
    out = tmp_path / "out" / "note.md"
    md.write_text("content", encoding="utf-8")
    result = to_markdown(md, output_path=out)
    assert result.output_path is not None
    assert result.output_path.read_text(encoding="utf-8") == "content"


def test_to_markdown_missing(tmp_path: Path):
    with pytest.raises(ToMarkdownError, match="không tồn tại"):
        to_markdown(tmp_path / "nope.pdf")


def test_to_markdown_unsupported_ext(tmp_path: Path):
    bad = tmp_path / "x.csv"
    bad.write_text("a,b\n", encoding="utf-8")
    with pytest.raises(ToMarkdownError, match="extension"):
        to_markdown(bad)


def test_pages_rejected_for_non_pdf(tmp_path: Path):
    md = tmp_path / "note.md"
    md.write_text("x", encoding="utf-8")
    with pytest.raises(ToMarkdownError, match="pages"):
        to_markdown(md, pages=[0])
