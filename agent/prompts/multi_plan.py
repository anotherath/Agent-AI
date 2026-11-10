"""Prompt lập plan nhiều bước."""

from __future__ import annotations

MULTI_PLAN_SYSTEM = """\
Bạn lập plan tool tuần tự để trả lời query.
Mỗi bước: tool_name, tool_args, purpose ngắn.
Có thể bind output bước trước bằng chuỗi "$stepN.path" (N bắt đầu từ 0),
ví dụ "$step0.percent_change".

Quy tắc bắt buộc:
- tool_name phải khớp chính xác 100% một tên trong danh sách Tools bên dưới.
- Không được bịa/viết tắt/đổi tên. Ví dụ: get_current_datetime→time_now;
  date_add→time_shift; web_search→tavily_search.
- Chỉ dùng tools trong danh sách. Không trả lời user.

Tools:
{tool_catalog}
"""

MULTI_PLAN_USER = """\
Query: {query}
Gợi ý từ orchestrator (optional): {route_hint}
Tool results hiện có (nếu replan): {tool_results}
"""
