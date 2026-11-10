"""Rubric gather_review: Jev Choice + LLM fallback."""

from __future__ import annotations

GATHER_REVIEW_INSTRUCTIONS = (
    "Sau khi chạy tool, quyết định bước tiếp theo để trả lời query. "
    "Chỉ phân loại; không viết câu trả lời cuối."
)

GATHER_REVIEW_CRITERIA: dict[str, str] = {
    "generate": "Đã đủ thông tin trong tool_results để trả lời query.",
    "single_tool": "Thiếu đúng một thông tin — cần gọi thêm một tool.",
    "multi_plan": "Thiếu nhiều bước / cần lập lại chuỗi tool.",
}

GATHER_REVIEW_LLM_SYSTEM = """\
Bạn review kết quả tool trước khi trả lời user.
Chọn next:
- generate: đủ thông tin
- single_tool: thiếu đúng 1 tool — điền tool_name (+ tool_args nếu chắc)
- multi_plan: thiếu nhiều bước, cần plan lại

tool_name phải khớp chính xác một tên trong danh sách Tools; không được bịa tên.

Query: {query}
Tool results (JSON):
{tool_results}

Tools có sẵn:
{tool_catalog}

Reason ngắn tiếng Việt.
"""
