# Kiến trúc Agent (LangGraph)

Tài liệu hub: Orchestrator phân luồng → Direct / Retrieve (+ Rerank) / Single tool / Multi-plan → Generate. Không dùng vòng ReAct thuần.

Khung dự án tổng: [`../architecture.md`](../architecture.md).

## Docs trong thư mục này

| File | Nội dung |
|---|---|
| [`agent-architecture.md`](./agent-architecture.md) | Hub: diagram, nguyên tắc, ví dụ luồng |
| [`routing-jev.md`](./routing-jev.md) | Jev + LLM fallback (orchestrator / gather_review) |
| [`state.md`](./state.md) | AgentState + schema quyết định |
| [`nodes.md`](./nodes.md) | Trách nhiệm từng node + edges |
| [`plan-execute.md`](./plan-execute.md) | multi_plan, `$stepN`, review budget |
| [`tools.md`](./tools.md) | Registry tools |
| [`generate-and-rag-ports.md`](./generate-and-rag-ports.md) | generate + port retrieve/rerank |

## Tổng quan

`agent/` chỉ lo **state, nodes, tools, prompts, routing, compile graph**.

Không xử lý FastAPI request, JWT, upload PDF — thuộc `app/` và `rag/`.

```text
                    START
                      │
                      ▼
                 ORCHESTRATOR
         (Jev → LLM nếu low conf)
                      │
        ┌─────────────┼──────────────┬─────────────────┐
        ▼             ▼              ▼                 ▼
     DIRECT        RETRIEVE      SINGLE_TOOL      MULTI_PLAN
   (trả lời)      (RAG PDF)     (1 tool)         (lập plan)
        │             │              │                 │
        │             ▼              ▼                 ▼
        │        candidates     tool_result      EXECUTE_PLAN
        │             │              │            (chạy lần lượt)
        │             ▼              │                 │
        │          RERANK            │                 │
        │             │              │                 │
        │          docs[]            │                 │
        │             │              │                 │
        │             └──────┬───────┘                 │
        │                    ▼                         ▼
        │                 GENERATE              GATHER_REVIEW
        │                    │            (Jev → LLM nếu low conf)
        │                    │                    │
        │                    │         ┌──────────┼──────────┐
        │                    │         ▼          ▼          ▼
        │                    │      GENERATE  SINGLE_TOOL  MULTI_PLAN
        │                    │         │       (thêm 1 tool) (plan lại)
        │                    │         │          │          │
        └────────────────────┴─────────┴──────────┴──────────┘
                                      │
                                     END
```

## Nguyên tắc

1. Orchestrator chỉ **phân loại + plan thô** — chi tiết: [`routing-jev.md`](./routing-jev.md).
2. **Jev** classify `orchestrator` / `gather_review`; confidence thấp → **LLM fallback**. Control flow ở LangGraph.
3. Jev **không** generate, **không** viết `plan[]` / `$stepN` — thuộc `generate` / `multi_plan`.
4. Mọi câu trả lời user qua **GENERATE**.
5. Multi-tool = plan list cứng — [`plan-execute.md`](./plan-execute.md).
6. **GATHER_REVIEW** có `max_review_loops`; hết budget → code ép `generate`.
7. RAG: **retrieve → rerank → generate** qua port — [`generate-and-rag-ports.md`](./generate-and-rag-ports.md).
8. Không lớp ReAct Thought/Action riêng.
9. FastAPI chỉ `graph.invoke` / `ainvoke`.
10. Interface routing (port) để đổi Jev ↔ LLM mà graph không đổi.

## Ví dụ luồng

### A. Trả lời luôn
`Chào bạn` → orchestrator `direct` → generate → END

### B. Một tool
`Giá BTC hiện tại?` → `single_tool(coingecko_price)` → generate → END

### C. RAG
`Trong file PDF tôi upload, mục 3 nói gì?` → retrieve → rerank → generate → END

### D. Nhiều tool + review
`BTC tăng bao nhiêu % so với 7 ngày trước?`
1. orchestrator → `multi_plan`
2. plan: time → coingecko history/price → calc %
3. execute_plan
4. gather_review → đủ → generate → END

## Cây file dự kiến (`agent/`)

```text
agent/
├── state.py
├── models.py        # ChatOpenAI factory (OPENAI_*)
├── graph.py
├── nodes/           # xem nodes.md
├── routing/         # xem routing-jev.md
├── tools/           # xem tools.md
└── prompts/
```

## Ranh giới repo

| Lớp | Việc |
|---|---|
| `app/` | HTTP, auth, upload, gọi `graph` |
| `rag/` | Ingest, embeddings, vectorstore, rerank impl; node gọi port |
| `agent/` | Điều phối suy luận + tools + generate |
| `workers/` | Job nền — không nằm trong graph chat |

## Thứ tự implement gợi ý

1. `state.py` — [`state.md`](./state.md)
2. `routing/` — [`routing-jev.md`](./routing-jev.md)
3. `nodes/orchestrator.py` + prompts
4. `generate` + `retrieve`/`rerank` (stub ok) — [`generate-and-rag-ports.md`](./generate-and-rag-ports.md)
5. `single_tool` + registry — [`tools.md`](./tools.md)
6. `multi_plan` + `execute_plan` — [`plan-execute.md`](./plan-execute.md)
7. `gather_review` + budget
8. `graph.py` + nối FastAPI chat
9. (Sau) rerank thật / GraphRAG trong `rag/`
