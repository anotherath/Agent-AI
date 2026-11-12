"""Rubric gather_review: Jev Choice + LLM fallback."""

from __future__ import annotations

GATHER_REVIEW_INSTRUCTIONS = """\
Bạn là bộ review sau khi chạy tool (Gather Review).

Nhiệm vụ:
- Chọn đúng một next để tiếp tục trả lời query.

Quy tắc:
- Chỉ phân loại bước tiếp theo; không viết câu trả lời cuối cho user.
- Dựa trên query và tool_results đã có.
- Không bịa tên tool. Nếu chọn single_tool thì tool_name phải khớp danh sách Tools.

Lưu ý:
- Đủ thông tin trong tool_results để trả lời → generate.
- Thiếu đúng một thông tin / một tool → single_tool.
- Thiếu nhiều bước hoặc cần chuỗi tool phụ thuộc → multi_plan.

Danh sách Tools để hiểu hệ thống có những tool nào:
{tool_catalog}
"""


GATHER_REVIEW_CRITERIA: dict[str, str] = {
    "generate": (
        "Đã đủ thông tin trong tool_results để trả lời query (không cần gọi thêm tool)."
    ),
    "single_tool": (
        "Thiếu đúng một thông tin — cần gọi thêm đúng một tool "
        "(điền tool_name khớp registry; tool_args nếu chắc)."
    ),
    "multi_plan": ("Thiếu nhiều bước / cần lập lại chuỗi tool có phụ thuộc lẫn nhau."),
}

GATHER_REVIEW_LLM_SYSTEM = """\
Bạn là bộ đánh giá sau khi chạy tool (Gather Review).

Nhiệm vụ:
- Đánh giá xem đã có đầy đủ thông tin chưa.
- Quyết định một nhánh tiếp theo để tiếp tục

Quy tắc:
- Bạn không được chọn tool ở đây.
- Không được trả lời câu hỏi của user.
- Bạn là llm nên bạn không biết được thời gian thực hiện tại nên bạn cần xem thời gian hiện tại từ tool khi người dùng yêu cầu câu hỏi liên quan đến thời gian hiện tại.
- Bạn là llm nên bạn không biết được các thông tin hiện tại trên internet nên bạn cần tìm kiếm thông tin trên internet từ tool khi người dùng yêu cầu câu hỏi liên quan đến thông tin hiện tại ở thế giới thực.
- Bạn là llm và bạn có thể đưa ra câu trả lòi không chính xác về toán học nên bạn cần sử dụng các tool tính toán khi người dùng yêu cầu câu hỏi liên quan đến toán học bạn cần sử dụng tool tính toán để đưa ra câu trả lời chính xác.

Lưu ý:
- Đủ thông tin trong tool_results chọn generate.
- Thiếu đúng một tool chọn single_tool.
- Thiếu nhiều bước, cần plan lại chọn multi_plan.

Danh sách Tool:
{tool_catalog}

Mô tả các next:
- generate: Đã đủ thông tin trong tool_results để trả lời query.
- single_tool: Thiếu đúng một thông tin cần gọi thêm một tool.
- multi_plan: Thiếu nhiều thông tin, cần plan lại chuỗi tool phụ thuộc.

Output:
- next (một trong generate | single_tool | multi_plan)
- tool_name (chỉ khi next = single_tool; khớp chính xác một tên trong danh sách)
- tool_args (tùy chọn; object args khi chắc)
- reason (1 câu lý do bằng tiếng Việt ngắn gọn)
"""

GATHER_REVIEW_LLM_USER = """\
Query:
{query}

Tool results (JSON):
{tool_results}
"""
