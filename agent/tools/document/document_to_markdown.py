"""Tool: document_to_markdown — wrapper quanh ``rag.ingest.to_markdown``."""

from __future__ import annotations

import json

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from agent.tools.document.descriptions import (
    DOCUMENT_TO_MARKDOWN,
    DOCUMENT_TO_MARKDOWN_OUTPUT_PATH,
    DOCUMENT_TO_MARKDOWN_PAGES,
    DOCUMENT_TO_MARKDOWN_PATH,
    DOCUMENT_TO_MARKDOWN_SOURCE_TYPE,
)
from rag.ingest import ToMarkdownError
from rag.ingest import to_markdown as convert_to_markdown


class DocumentToMarkdownInput(BaseModel):
    path: str = Field(description=DOCUMENT_TO_MARKDOWN_PATH)
    source_type: str | None = Field(
        default=None,
        description=DOCUMENT_TO_MARKDOWN_SOURCE_TYPE,
    )
    output_path: str | None = Field(
        default=None,
        description=DOCUMENT_TO_MARKDOWN_OUTPUT_PATH,
    )
    pages: list[int] | None = Field(
        default=None,
        description=DOCUMENT_TO_MARKDOWN_PAGES,
    )


def _to_tool_result(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


def document_to_markdown(
    path: str,
    source_type: str | None = None,
    output_path: str | None = None,
    pages: list[int] | None = None,
) -> str:
    """Gọi ``rag.ingest.to_markdown``; trả JSON string cho agent."""
    try:
        result = convert_to_markdown(
            path,
            source_type=source_type,
            output_path=output_path,
            pages=pages,
        )
        return _to_tool_result(
            {
                "source_path": str(result.source_path),
                "source_type": result.source_type.value,
                "output_path": str(result.output_path) if result.output_path else None,
                "pages": result.pages,
                "char_count": result.char_count,
                "markdown": result.markdown,
            }
        )
    except ToMarkdownError as exc:
        return _to_tool_result({"error": str(exc)})
    except Exception as exc:  # noqa: BLE001
        return _to_tool_result({"error": str(exc)})


def get_document_to_markdown_tool() -> StructuredTool:
    return StructuredTool.from_function(
        name="document_to_markdown",
        description=DOCUMENT_TO_MARKDOWN,
        func=document_to_markdown,
        args_schema=DocumentToMarkdownInput,
    )
