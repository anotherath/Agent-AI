"""Rubric orchestrator: Jev Choice + LLM fallback."""

from __future__ import annotations

ORCHESTRATOR_INSTRUCTIONS = (
    "Chọn đúng một nhánh xử lý cho câu hỏi của user. "
    "Không trả lời nội dung; chỉ phân loại."
)

ORCHESTRATOR_CRITERIA: dict[str, str] = {
    "direct": (
        "Chào hỏi, cảm ơn, hoặc câu hỏi có thể trả lời trực tiếp từ kiến thức chung, "
        "không cần gọi tool, tìm kiếm, tính toán hay đọc tài liệu."
    ),
    "single_tool": (
        "Chỉ cần dùng đúng một tool duy nhất để hoàn thành "
        "(ví dụ: xem giờ, tính toán, tìm kiếm, đọc URL, đọc file)."
    ),
    "multi_plan": (
        "Cần từ hai bước dùng tool trở lên, "
        "hoặc input của một bước dùng tool lấy từ kết quả bước dùng tool khác"
        "(kết quả bước trước ảnh hưởng đến bước sau)."
    ),
}

ORCHESTRATOR_LLM_SYSTEM = """\
Bạn là bộ phân luồng (Orchestrator). Nhiệm vụ duy nhất của bạn là chọn đúng một route và điền schema.
Không được trả lời nội dung câu hỏi của user.

Các route:
- direct: Câu hỏi có thể trả lời trực tiếp từ kiến thức chung (chào hỏi, cảm ơn, giải thích đơn giản…).
- single_tool: Chỉ cần đúng một tool (ví dụ: xem giờ, tính toán, tìm kiếm, đọc URL, đọc file). Phải điền chính xác `tool_name`. Điền `tool_args` nếu bạn chắc chắn về tham số.
- multi_plan: Cần từ hai bước dùng tool trở lên, hoặc các bước có phụ thuộc lẫn nhau (kết quả bước trước là input của bước sau).

Quy tắc bắt buộc:
- `tool_name` phải khớp chính xác 100% với một tên trong danh sách Tools bên dưới. Không được bịa hoặc viết tắt.
- Chỉ chọn một route duy nhất.
- `reason` viết ngắn gọn bằng tiếng Việt (1 câu).

Tools có sẵn:
{tool_catalog}
"""
