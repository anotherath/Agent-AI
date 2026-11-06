"""Tool: PDF → Markdown — thin wrapper quanh ``rag.ingest.pdf_to_markdown``."""

from __future__ import annotations

import json

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from agent.tools.pdf.descriptions import PDF_TO_MARKDOWN
from rag.ingest import PdfToMarkdownError, pdf_to_markdown as convert_pdf_to_markdown


class PdfToMarkdownInput(BaseModel):
    pdf_path: str = Field(description="Đường dẫn tuyệt đối hoặc tương đối tới file PDF")
    output_path: str | None = Field(
        default=None,
        description="Nếu set, ghi Markdown ra đường dẫn này (.md). Null = chỉ trả nội dung.",
    )
    pages: list[int] | None = Field(
        default=None,
        description="Danh sách số trang 0-based cần chuyển. Null = mọi trang.",
    )


def _to_tool_result(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


def pdf_to_markdown(
    pdf_path: str,
    output_path: str | None = None,
    pages: list[int] | None = None,
) -> str:
    """Gọi ``rag.ingest.pdf_to_markdown``; trả JSON string cho agent."""
    try:
        result = convert_pdf_to_markdown(
            pdf_path,
            output_path=output_path,
            pages=pages,
        )
        return _to_tool_result(
            {
                "pdf_path": str(result.pdf_path),
                "output_path": str(result.output_path) if result.output_path else None,
                "pages": result.pages,
                "char_count": result.char_count,
                "markdown": result.markdown,
            }
        )
    except PdfToMarkdownError as exc:
        return _to_tool_result({"error": str(exc)})
    except Exception as exc:  # noqa: BLE001
        return _to_tool_result({"error": str(exc)})


def get_pdf_to_markdown_tool() -> StructuredTool:
    return StructuredTool.from_function(
        name="pdf_to_markdown",
        description=PDF_TO_MARKDOWN,
        func=pdf_to_markdown,
        args_schema=PdfToMarkdownInput,
    )
