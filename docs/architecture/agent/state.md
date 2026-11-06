# Agent state & contracts

Hub: [`agent-architecture.md`](./agent-architecture.md) · Routing: [`routing-jev.md`](./routing-jev.md)

## Mục đích

Định nghĩa state LangGraph và schema quyết định mà nodes đọc/ghi. Một nguồn sự thật cho contract giữa orchestrator, tools, RAG ports và generate.

## Làm / không làm

| Làm | Không làm |
|---|---|
| Khai báo field state + default | Logic HTTP / JWT |
| Schema `RouteDecision` / `ReviewDecision` / `PlanStep` | Implement retrieve/embed |
| Giữ typed, serializable | Nhét raw FastAPI request vào state |

## AgentState (tối thiểu)

```text
query: str
user_id: str
messages: list

route: RouteDecision | null
review: ReviewDecision | null
plan: list[PlanStep]
step_index: int

documents_candidates: list   # sau retrieve (rộng)
documents: list              # sau rerank (hẹp → generate)
retrieve_k: int              # default 20
rerank_top_n: int            # default 5

tool_results: list           # [{step, tool, args, result, ok}]

review_count: int
max_review_loops: int        # default 2
jev_confidence_threshold: float   # default ~0.6–0.7

answer: str
```

## RouteDecision

Output của `orchestrator` (Jev hoặc LLM fallback).

```text
route: direct | retrieve | single_tool | multi_plan
need_retrieve: bool
tool_name: str | null
tool_args: dict | null
plan: list[PlanStep] | null   # plan thô optional; chi tiết ở multi_plan
reason: str
confidence: float | null      # từ Jev; null nếu LLM fallback
decided_by: jev | llm
```

| `route` | Khi nào |
|---|---|
| `direct` | Chào hỏi / kiến thức sẵn có |
| `retrieve` | Hỏi PDF / knowledge đã ingest |
| `single_tool` | Một nguồn (giá, search, calc, giờ…) |
| `multi_plan` | ≥2 bước có phụ thuộc |

## ReviewDecision

Output của `gather_review`.

```text
next: generate | single_tool | multi_plan
tool_name: str | null      # gợi ý nếu next=single_tool; null → LLM điền sau
confidence: float | null
decided_by: jev | llm
```

## PlanStep

```text
tool_name: str
tool_args: dict          # literal hoặc "$stepN.path"
purpose: str             # debug / review
```

Chi tiết resolve: [`plan-execute.md`](./plan-execute.md).

## tool_results entry

```text
step: int
tool: str
args: dict               # đã resolve
result: any
ok: bool
```

## Code dự kiến

`agent/state.py` — TypedDict / Pydantic models dùng chung nodes.

## Khi đổi gì thì đụng đâu

- Thêm field graph → `state.py` + node đọc/ghi + doc này  
- Đổi schema route/review → `state` + `routing/` + prompts  
- Đổi shape documents → port RAG + generate (xem [`generate-and-rag-ports.md`](./generate-and-rag-ports.md))
