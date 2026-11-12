"""Mô tả tools nhóm search (Tavily) — description + parameters."""

# ---------------------------------------------------------------------------
# name: tavily_search
# ---------------------------------------------------------------------------
TAVILY_SEARCH = (
    "Tìm kiếm trên web qua Tavily, trả về danh sách trang kèm đoạn trích (snippet).\n"
    "Dùng khi cần thông tin từ internet nhưng chưa có URL cụ thể "
    "(tin tức, tra cứu, 'ai nói gì về…').\n"
    "Input: query (chuỗi tìm kiếm).\n"
    "Output: JSON {query, results[{title, url, content}], answer?}.\n"
    "Lưu ý: snippet không phải full page — đã có URL cần đọc sâu thì dùng tavily_extract. "
    "Có rate limit/credit Tavily."
)

# parameters: tavily_search
TAVILY_SEARCH_QUERY = "string (bắt buộc) - Câu truy vấn tìm kiếm."
TAVILY_SEARCH_MAX_RESULTS = (
    "integer (tùy chọn) - Số kết quả tối đa trả về (mặc định 5)."
)
TAVILY_SEARCH_SEARCH_DEPTH = (
    'string (tùy chọn) - "basic" | "advanced" (mặc định basic).'
)
TAVILY_SEARCH_INCLUDE_ANSWER = (
    "boolean (tùy chọn) - true để kèm câu trả lời ngắn từ Tavily (mặc định true)."
)

# ---------------------------------------------------------------------------
# name: tavily_extract
# ---------------------------------------------------------------------------
TAVILY_EXTRACT = (
    "Đọc nội dung một trang web theo URL qua Tavily Extract, trả về content đã làm sạch.\n"
    "Dùng khi người dùng đưa link trực tiếp, hoặc sau tavily_search khi cần đọc đầy đủ một trang.\n"
    "Input: url (bắt buộc); extract_depth, format (tùy chọn).\n"
    "Output: JSON {url, title?, content, extract_depth, format} — đã bỏ ảnh/nav/JS chrome, có trần độ dài.\n"
    "Lưu ý:\n"
    "- Trang login, paywall hoặc chặn bot có thể bị fail.\n"
    "- extract_depth=advanced đọc tốt hơn với trang nhiều JS hoặc bảng, nhưng tốn credit hơn."
)

# parameters: tavily_extract
TAVILY_EXTRACT_URL = (
    "string (bắt buộc) - URL trang cần đọc (ví dụ: https://example.com/article)."
)
TAVILY_EXTRACT_EXTRACT_DEPTH = (
    'string (tùy chọn) - Độ sâu trích xuất: "basic" | "advanced" (mặc định basic).'
)
TAVILY_EXTRACT_FORMAT = (
    'string (tùy chọn) - Định dạng trả về: "markdown" | "text" (mặc định markdown).'
)
