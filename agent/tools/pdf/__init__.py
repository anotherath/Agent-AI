"""PDF tools — agent wrappers quanh ``rag.ingest``."""

from __future__ import annotations

from langchain_core.tools import BaseTool

from agent.tools.pdf.to_markdown import get_pdf_to_markdown_tool, pdf_to_markdown


def get_pdf_tools() -> list[BaseTool]:
    return [get_pdf_to_markdown_tool()]


__all__ = ["get_pdf_tools", "get_pdf_to_markdown_tool", "pdf_to_markdown"]
