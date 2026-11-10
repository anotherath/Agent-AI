"""Unit tests document → Markdown agent tool."""

from __future__ import annotations

import json
from pathlib import Path

import pymupdf
from docx import Document

from agent.tools.document import get_document_tools
from agent.tools.document.document_to_markdown import document_to_markdown
from tests.conftest import show_tool_result


def _make_sample_pdf(path: Path) -> None:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Hello PDF to Markdown\n\nSection One")
    doc.save(path)
    doc.close()


def test_document_registry():
    names = {t.name for t in get_document_tools()}
    assert names == {"document_to_markdown"}


def test_document_to_markdown_pdf(tmp_path: Path):
    pdf = tmp_path / "sample.pdf"
    _make_sample_pdf(pdf)

    data = json.loads(document_to_markdown(str(pdf)))
    show_tool_result("document_to_markdown(sample.pdf)", data)

    assert "error" not in data
    assert data["source_type"] == "pdf"
    assert data["char_count"] > 0


def test_document_to_markdown_md(tmp_path: Path):
    md = tmp_path / "note.md"
    md.write_text("# Hi\n\nBody\n", encoding="utf-8")
    data = json.loads(document_to_markdown(str(md)))
    show_tool_result("document_to_markdown(note.md)", data)
    assert data["source_type"] == "markdown"
    assert "# Hi" in data["markdown"]


def test_document_to_markdown_docx(tmp_path: Path):
    path = tmp_path / "sample.docx"
    doc = Document()
    doc.add_heading("Word Doc", level=1)
    doc.add_paragraph("Paragraph text")
    doc.save(path)

    data = json.loads(document_to_markdown(str(path)))
    show_tool_result("document_to_markdown(sample.docx)", data)
    assert "error" not in data
    assert data["source_type"] == "docx"
    assert "Word Doc" in data["markdown"]


def test_document_to_markdown_missing(tmp_path: Path):
    data = json.loads(document_to_markdown(str(tmp_path / "nope.pdf")))
    assert "error" in data
