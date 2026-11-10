# Routing: Jev + LLM fallback

Hub: [`agent-architecture.md`](./agent-architecture.md) · State: [`state.md`](./state.md)

## Mục đích

Phân nhánh graph bằng classifier nhanh (Jev). Confidence thấp → LLM structured output **cùng schema**. Control flow vẫn thuộc LangGraph/code.

## Làm / không làm

| Làm | Không làm |
|---|---|
| Choice route / review + confidence | Generate câu trả lời cho user |
| Fallback LLM khi low confidence | Viết `plan[]` chi tiết / `$stepN` |
| Log `decided_by`, `confidence` | Gọi tool / retrieve trực tiếp |
| Port đổi được Jev ↔ LLM | Sở hữu `max_review_loops` (code graph) |

## Flow chung

```text
state (query / tool_results / …)
        │
        ▼
      Jev  →  typed decision + confidence
        │
        ├─ confidence >= threshold  →  dùng quyết định Jev
        └─ confidence <  threshold  →  LLM structured output (cùng schema)
        │
        ▼
   LangGraph conditional edges
```

Tham chiếu: [TypeSafe Jev / System One](https://typesafe.ai/blog/introducing-system-one-models-and-jev).

Jev qua `typesafe_sdk` + `TYPESAFE_API_KEY` (API TypeSafe chính ngạch). Model: `TYPESAFE_DEFAULT_MODEL` (vd. `jev-latest`). Thiếu key / SDK / lỗi → `classify_choice` trả `None` → LLM fallback.

## Áp dụng theo node

| Node | Jev Choice | Không làm |
|---|---|---|
| `orchestrator` | `direct \| retrieve \| single_tool \| multi_plan` (+ optional tool Choice nếu registry nhỏ) | Plan `$stepN`, generate |
| `gather_review` | `generate \| single_tool \| multi_plan` | Điền `tool_args` / plan chi tiết; **bỏ qua** khi hết `max_review_loops` |

## Ranh giới trách nhiệm

| Việc | Ai |
|---|---|
| Route thô 4 nhánh | Jev → LLM nếu low conf |
| Review sau execute | Jev → LLM nếu low conf |
| Plan nhiều bước / `$stepN` | LLM (`multi_plan`) — xem [`plan-execute.md`](./plan-execute.md) |
| Tool args phức tạp | LLM / resolve trong `execute_plan` |
| Generate | LLM luôn — xem [`generate-and-rag-ports.md`](./generate-and-rag-ports.md) |

## Config

| Knob | Gợi ý |
|---|---|
| `jev_confidence_threshold` | `0.6`–`0.7` — log % fallback / lỗi route rồi chỉnh |
| Early access Jev | Giữ port trong `agent/routing/` để đổi backend |

## Code dự kiến

```text
agent/routing/
├── types.py          # helpers schema / mapping
├── jev_client.py     # gọi Jev Choice
└── llm_fallback.py   # structured LLM khi low conf
```

Nodes gọi port này; không nhúng vendor SDK trực tiếp vào mọi node.

## Khi đổi gì thì đụng đâu

- Đổi threshold / logging → `routing/` + config state  
- Đổi options Choice → prompts rubric + `jev_client`  
- Đổi vendor classifier → chỉ `routing/` (graph giữ nguyên)
