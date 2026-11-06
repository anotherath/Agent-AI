"""Unit tests PDF → Markdown tool."""

from __future__ import annotations

import json
from pathlib import Path

import pymupdf

from agent.tools.pdf import get_pdf_tools, pdf_to_markdown
from tests.conftest import show_tool_result


def _make_sample_pdf(path: Path) -> None:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Hello PDF to Markdown\n\nSection One")
    doc.save(path)
    doc.close()


def test_pdf_registry():
    names = {t.name for t in get_pdf_tools()}
    assert names == {"pdf_to_markdown"}


def test_pdf_to_markdown_basic(tmp_path: Path):
    pdf = tmp_path / "sample.pdf"
    _make_sample_pdf(pdf)

    data = json.loads(pdf_to_markdown(str(pdf)))
    show_tool_result("pdf_to_markdown(sample.pdf)", data)

    assert "error" not in data
    assert data["char_count"] > 0
    assert "Hello" in data["markdown"] or "Section" in data["markdown"]


def test_pdf_to_markdown_write_output(tmp_path: Path):
    pdf = tmp_path / "sample.pdf"
    out = tmp_path / "out" / "sample.md"
    _make_sample_pdf(pdf)

    data = json.loads(pdf_to_markdown(str(pdf), output_path=str(out)))
    show_tool_result("pdf_to_markdown(+output)", data)

    assert "error" not in data
    assert Path(data["output_path"]).is_file()
    assert Path(data["output_path"]).read_text(encoding="utf-8") == data["markdown"]


def test_pdf_to_markdown_missing_file(tmp_path: Path):
    data = json.loads(pdf_to_markdown(str(tmp_path / "nope.pdf")))
    assert "error" in data
