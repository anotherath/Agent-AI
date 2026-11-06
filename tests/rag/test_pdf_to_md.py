"""Unit tests cho ``rag.ingest.pdf_to_md``."""

from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest

from rag.ingest.pdf_to_md import PdfToMarkdownError, pdf_to_markdown


def _make_sample_pdf(path: Path) -> None:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Hello PDF to Markdown\n\nSection One")
    doc.save(path)
    doc.close()


def test_pdf_to_markdown_basic(tmp_path: Path):
    pdf = tmp_path / "sample.pdf"
    _make_sample_pdf(pdf)

    result = pdf_to_markdown(pdf)

    assert result.pdf_path == pdf.resolve()
    assert result.output_path is None
    assert result.char_count > 0
    assert "Hello" in result.markdown or "Section" in result.markdown


def test_pdf_to_markdown_write_output(tmp_path: Path):
    pdf = tmp_path / "sample.pdf"
    out = tmp_path / "out" / "sample.md"
    _make_sample_pdf(pdf)

    result = pdf_to_markdown(pdf, output_path=out)

    assert result.output_path is not None
    assert result.output_path.is_file()
    assert result.output_path.read_text(encoding="utf-8") == result.markdown


def test_pdf_to_markdown_missing_file(tmp_path: Path):
    with pytest.raises(PdfToMarkdownError, match="không tồn tại"):
        pdf_to_markdown(tmp_path / "nope.pdf")


def test_pdf_to_markdown_not_pdf(tmp_path: Path):
    txt = tmp_path / "note.txt"
    txt.write_text("hi", encoding="utf-8")
    with pytest.raises(PdfToMarkdownError, match="Không phải PDF"):
        pdf_to_markdown(txt)
