"""Mô tả tools nhóm document — description + parameters."""

# ---------------------------------------------------------------------------
# name: document_to_markdown
# ---------------------------------------------------------------------------
DOCUMENT_TO_MARKDOWN = (
    "Chuyển tài liệu local (PDF, DOCX, Markdown, TXT) sang Markdown để đọc hoặc tóm tắt.\n"
    "Dùng khi người dùng yêu cầu đọc, tóm tắt hoặc trích xuất nội dung từ file trên máy.\n"
    "Input: path (bắt buộc); source_type, output_path, pages (tùy chọn).\n"
    "Output: JSON gồm source_path, source_type, pages, char_count, markdown "
    "(và output_path nếu ghi file).\n"
    "Lưu ý: PDF chỉ hỗ trợ text layer (không OCR). Với PDF dài nên chỉ định pages. "
    "Chỉ đọc file local, không hỗ trợ URL."
)

DOCUMENT_TO_MARKDOWN_PATH = "string (bắt buộc) - Đường dẫn tới file cần chuyển."
DOCUMENT_TO_MARKDOWN_SOURCE_TYPE = (
    'string (tùy chọn) - "pdf" | "docx" | "markdown" | "text". '
    "Để trống sẽ tự nhận theo extension."
)
DOCUMENT_TO_MARKDOWN_OUTPUT_PATH = (
    "string (tùy chọn) - Nếu set, ghi Markdown ra đường dẫn .md này. "
    "Bỏ trống = chỉ trả nội dung."
)
DOCUMENT_TO_MARKDOWN_PAGES = (
    "array of integer (tùy chọn) - Số trang cần lấy (0-based), chỉ dùng với PDF. "
    "Bỏ trống = mọi trang."
)
