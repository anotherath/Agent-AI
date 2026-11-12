# AGENTS.md — quy ước cho AI làm việc trên repo

## Supabase = Postgres only

Supabase trong dự án **chỉ** dùng làm **PostgreSQL** (connection string / SQLAlchemy).

- **Được:** `DATABASE_URL` trỏ tới Postgres (pooler) của Supabase; schema/migration/query qua SQLAlchemy.
- **Không được:** Supabase Auth, Supabase Realtime, Storage SDK, Edge Functions, `supabase-py`, RLS thay cho auth app, hay bất kỳ API Supabase nào ngoài Postgres.

Auth (Google OAuth, session cookie, …) làm trên FastAPI/`app/`, không dùng Supabase Auth.

---

## Đặt tên file trong `agent/`

Tên file Python dưới `agent/` dùng **danh từ / cụm danh từ** (`snake_case`), không dùng động từ đứng trước.

- Đúng: `tool_select.py`, `tool_execution.py`, `orchestrator.py`
- Sai: `execute_tool.py`, `select_tool.py`, `invoke_tool.py`

Helper (không phải LangGraph node) đặt trong `agent/nodes/util/`, vẫn tên danh từ.

- Node: `agent/nodes/tool_select.py`, `agent/nodes/tool_execution.py`
- Helper: `agent/nodes/util/tool_invocation.py`, `agent/nodes/util/arg_resolution.py`, `agent/nodes/util/tool_pick.py`

---

## Cách viết tool (một chuẩn duy nhất)

Mọi tool trong `agent/tools/` theo **một** pattern:

1. Dùng `StructuredTool.from_function` + Pydantic `args_schema`.
2. Logic gọi API/lib nằm trong hàm Python của mình (vd. `TavilyClient`) — **không** dùng wrapper LangChain có sẵn (vd. `TavilySearchResults`) vì mất kiểm soát schema và mô tả parameter.
3. File implement **trùng tên tool**: `tavily_search.py`, `tavily_extract.py`, …
4. Factory: `get_<tool_name>_tool()` → đăng ký trong `get_<group>_tools()` / `get_tools()`.
5. **Không** re-export function trùng tên module trong `__init__.py` của package (tránh shadow submodule).

Ví dụ cấu trúc nhóm search:

```text
agent/tools/search/
├── __init__.py           # get_search_tools()
├── client.py             # helper dùng chung (API key, JSON result…)
├── descriptions.py       # toàn bộ mô tả tool + param
├── tavily_search.py
└── tavily_extract.py
```

---

## Gom hết mô tả tool vào một file

Mỗi nhóm tool có **một** file `descriptions.py` trong package đó (vd. `agent/tools/search/descriptions.py`).

Trong file đó, với mỗi tool:

1. Comment `# name: <tool_name>`
2. Hằng **description** của tool (`UPPER_SNAKE_CASE` theo tên tool)
3. Các hằng **parameter** (`TOOLNAME_PARAMNAME`)

File implement chỉ **import** các hằng đó vào `description=` và `Field(description=...)` — không viết mô tả dài rải trong code tool.

```python
# descriptions.py
# name: tavily_search
TAVILY_SEARCH = ...
TAVILY_SEARCH_QUERY = "..."

# tavily_search.py
from agent.tools.search.descriptions import TAVILY_SEARCH, TAVILY_SEARCH_QUERY


class SearchInput(BaseModel):
    query: str = Field(description=TAVILY_SEARCH_QUERY)


StructuredTool.from_function(
    name="tavily_search",
    description=TAVILY_SEARCH,
    func=tavily_search,
    args_schema=SearchInput,
)
```

---

## Cách viết mô tả tool

Khi viết mô tả tool, luôn tuân theo cấu trúc sau:

1. Tên biến phải là `UPPER_SNAKE_CASE` theo tên tool.
2. Description viết bằng multi-line string, gồm các phần:
   - Tool làm gì (1 câu ngắn).
   - Dùng khi nào (nêu rõ tình huống sử dụng).
   - Input nhận gì (tóm tắt tham số chính; chi tiết từng param vẫn ở hằng parameter).
   - Output trả về là gì.
   - Lưu ý quan trọng (chỉ thêm khi thật sự cần).
3. Parameters viết riêng thành các hằng số, format cố định:

   `TOOLNAME_PARAMNAME = "type (bắt buộc|tùy chọn) - mô tả ngắn gọn."`

### Ví dụ mẫu (bắt buộc phải theo)

```python
TAVILY_SEARCH = (
    "Tìm kiếm trên web qua Tavily, trả về danh sách trang kèm đoạn trích (snippet).\n"
    "Dùng khi cần thông tin từ internet nhưng chưa có URL cụ thể "
    "(tin tức, tra cứu, 'ai nói gì về…').\n"
    "Input: query (chuỗi tìm kiếm).\n"
    "Output: list kết quả với title, url, content/snippet.\n"
    "Lưu ý: snippet không phải full page — đã có URL cần đọc sâu thì dùng tavily_extract. "
    "Có rate limit/credit Tavily."
)

TAVILY_SEARCH_QUERY = "string (bắt buộc) - Câu truy vấn tìm kiếm."
TAVILY_SEARCH_MAX_RESULTS = (
    "integer (tùy chọn) - Số kết quả tối đa trả về (mặc định 5)."
)
```

### Quy tắc

- Không được viết description chung chung.
- Bắt buộc có phần **"Dùng khi"**, **"Input"** và **"Output"**.
- Luôn viết bằng **tiếng Việt**, ngắn gọn, rõ ràng (nên từ 4–8 dòng).
- Chỉ thêm phần **"Lưu ý"** khi thật sự cần (hạn chế, dễ dùng sai, tốn credit…). Không ép phải có.
- Description nên tập trung vào việc hướng dẫn model **khi nào** và **cách** dùng tool, không viết dài dòng.

Tham chiếu đang dùng: `agent/tools/search/descriptions.py`.
