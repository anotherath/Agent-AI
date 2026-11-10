# Tools registry

Hub: [`agent-architecture.md`](./agent-architecture.md) · Plan: [`plan-execute.md`](./plan-execute.md)

## Mục đích

Local tools (LangChain `BaseTool`) gắn vào `single_tool` / `execute_plan` qua registry.

## Làm / không làm

| Làm | Không làm |
|---|---|
| `get_tools()` gom theo nhóm thư mục | Biết FastAPI / JWT |
| Description rõ để router/planner chọn đúng | Trả lời user trực tiếp (phải qua `generate`) |
| Unit + live tests theo nhóm | Nhúng business HTTP vào tool |

## Entry point

```text
agent.tools.get_tools() → list[BaseTool]
```

Dùng bởi `nodes/single_tool.py` và `nodes/execute_plan.py` (lookup theo `tool_name`).

## Nhóm hiện có

| Package | Tools |
|---|---|
| `search/` | `tavily_search`, `tavily_extract` (đọc URL) |
| `calc/` | `calc_evaluate`, `calc_solve`, `calc_diff`, `calc_integrate`, `calc_percent_change` |
| `timeutil/` | `time_now`, `time_convert`, `time_shift` |
| `document/` | `document_to_markdown` — wrapper gọi `rag.ingest.to_markdown` (pdf/md/txt/docx) |

Mô tả chi tiết nằm trong `descriptions.py` (hoặc docstring) từng nhóm — giữ đồng bộ với prompt orchestrator / multi_plan.

## Cây thư mục

```text
agent/tools/
├── __init__.py              # get_tools()
├── search/
│   ├── tavily_search.py
│   ├── tavily_extract.py
│   ├── descriptions.py
│   └── client.py
├── calc/                    # SymPy
├── timeutil/
└── document/                # wrapper → rag.ingest.to_markdown
```

## Convention thêm tool mới

1. File (hoặc nhóm) dưới `agent/tools/<group>/`  
2. Export factory `get_*_tool()` / `get_*_tools()`  
3. Đăng ký trong `get_tools()`  
4. Description ngắn, khi nào dùng / không dùng  
5. Test: `tests/agent/tools/<group>/`  
6. Nếu hay dùng trong multi-step: ghi ví dụ `$stepN` vào [`plan-execute.md`](./plan-execute.md) nếu cần

## Gắn vào graph

| Node | Cách dùng |
|---|---|
| `single_tool` | Một `tool_name` (+ args) từ `route` / `review` |
| `execute_plan` | Từng `PlanStep.tool_name` sau khi resolve args |
| `orchestrator` / Jev | Chỉ **chọn** tool khi cần; không invoke |

## Env / secrets (tool)

| Biến | Tool |
|---|---|
| `TAVILY_API_KEY` | `tavily_search`, `tavily_extract` |

Không commit secrets; đọc từ env / `.env`.

## Khi đổi gì thì đụng đâu

- Thêm/xóa tool → package + `get_tools()` + tests + (optional) routing rubric  
- Đổi schema output tool → có thể ảnh hưởng `$stepN.path` trong plan  
- Đổi sang MCP sau này → adapter trong group, registry vẫn `get_tools()`
