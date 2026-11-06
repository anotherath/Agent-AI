# Nodes & edges

Hub: [`agent-architecture.md`](./agent-architecture.md) · State: [`state.md`](./state.md)

## Mục đích

Mô tả từng node graph: trách nhiệm, đọc/ghi state, cạnh đi tiếp. Không chứa logic vendor (Jev SDK, vector DB) — chỉ gọi port.

## Làm / không làm

| Làm | Không làm |
|---|---|
| Một việc rõ / node | Auth, upload PDF, HTTP |
| Ghi field state đã định | Gọi LLM generate ngoài node `generate` |
| Conditional edge theo `route` / `review` | ReAct Thought/Action tự do |

## Bảng nodes

| Node | Việc | Đọc chính | Ghi chính | Đi tiếp |
|---|---|---|---|---|
| `orchestrator` | Jev→LLM → `RouteDecision` | `query`, `messages` | `route` | theo `route.*` |
| `retrieve` | Port RAG lấy candidates | `query`, `user_id`, `retrieve_k` | `documents_candidates` | `rerank` |
| `rerank` | Port RAG xếp lại / cắt top-n | `query`, `documents_candidates`, `rerank_top_n` | `documents` | `generate` |
| `single_tool` | Gọi 1 tool registry | `route` / `review`, tools | `tool_results` | `generate` (hoặc review nếu từ gather) |
| `multi_plan` | LLM lập `plan[]` chi tiết | `query`, `route`, tools schema | `plan` | `execute_plan` |
| `execute_plan` | Chạy tuần tự + resolve `$stepN` | `plan`, `tool_results` | `tool_results`, `step_index` | `gather_review` |
| `gather_review` | Jev→LLM → `ReviewDecision` | `query`, `tool_results`, `review_count` | `review`, `review_count` | theo `review.next` |
| `generate` | LLM → `answer` | `query`, `documents`, `tool_results` | `answer` | END |

Chi tiết routing: [`routing-jev.md`](./routing-jev.md) · Plan: [`plan-execute.md`](./plan-execute.md) · RAG ports: [`generate-and-rag-ports.md`](./generate-and-rag-ports.md).

## Edges (tóm tắt)

```text
START → orchestrator
orchestrator → generate          # direct (có thể coi direct = generate luôn)
orchestrator → retrieve → rerank → generate
orchestrator → single_tool → generate
orchestrator → multi_plan → execute_plan → gather_review

gather_review → generate
gather_review → single_tool → … → gather_review | generate
gather_review → multi_plan → execute_plan → gather_review

(*) hết max_review_loops → generate (code ép, không gọi Jev)
```

Diagram đầy đủ: hub [`agent-architecture.md`](./agent-architecture.md).

## File dự kiến

```text
agent/nodes/
├── orchestrator.py
├── retrieve.py
├── rerank.py
├── single_tool.py
├── multi_plan.py
├── execute_plan.py
├── gather_review.py
└── generate.py
```

`graph.py` compile nodes + conditional edges.

## Khi đổi gì thì đụng đâu

- Thêm nhánh route → `nodes` + `graph` + `RouteDecision` + routing rubric  
- Đổi hành vi review → `gather_review` + `ReviewDecision` + budget trong graph  
- Đổi retrieve/rerank internals → `rag/` (node chỉ giữ port call)
