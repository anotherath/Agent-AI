"""Document tools — agent wrappers quanh ``rag.ingest.to_markdown``."""

from __future__ import annotations

from langchain_core.tools import BaseTool

from agent.tools.document.document_to_markdown import get_document_to_markdown_tool


def get_document_tools() -> list[BaseTool]:
    return [get_document_to_markdown_tool()]


__all__ = [
    "get_document_tools",
    "get_document_to_markdown_tool",
]
