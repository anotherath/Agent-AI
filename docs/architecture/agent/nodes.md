# Nodes & edges

Hub: [`agent-architecture.md`](./agent-architecture.md) · State: [`state.md`](./state.md)

## Mục đích

Mô tả từng node graph: trách nhiệm, đọc/ghi state, cạnh đi tiếp. Không chứa logic vendor (Jev SDK, vector DB) — chỉ gọi port.

## Làm / không làm

| Làm | Không làm |
|---|---|
| Một việc rõ / node | Auth, upload PDF, HTTP |
| Ghi field state đã định | Gọi LLM generate ngoài node `generate` |
| Conditional edge theo `route` / `review` / `guard` | ReAct Thought/Action tự do |

## Bảng nodes

| Node | Việc | Đọc chính | Ghi chính | Đi tiếp |
|---|---|---|---|---|
| `input_guard` | Port check query → `GuardDecision`; refuse thì ghi template | `query` | `guard`, `answer` (nếu refuse) | allow → orchestrator; refuse → END |
| `orchestrator` | Jev→LLM → `RouteDecision` | `query`, `messages` | `route` | theo `route.*` |
| `retrieve` | Port RAG lấy candidates | `query`, `user_id`, `retrieve_k` | `documents_candidates` | `rerank` |
| `rerank` | Port RAG xếp lại / cắt top-n | `query`, `documents_candidates`, `rerank_top_n` | `documents` | `generate` |
| `single_tool` | Gọi 1 tool registry | `route` / `review`, tools | `tool_results` | `generate` (hoặc review nếu từ gather) |
| `multi_plan` | LLM lập `plan[]` chi tiết | `query`, `route`, tools schema | `plan` | `execute_plan` |
| `execute_plan` | Chạy tuần tự + resolve `$stepN` | `plan`, `tool_results` | `tool_results`, `step_index` | `gather_review` |
| `gather_review` | Jev→LLM → `ReviewDecision` | `query`, `tool_results`, `review_count` | `review`, `review_count` | theo `review.next` |
| `generate` | LLM → `answer` | `query`, `documents`, `tool_results` | `answer` | `output_guard` |
| `output_guard` | Port check answer → có thể sửa `answer` | `answer`, `guard` | `answer`, `guard` | END |

Chi tiết routing: [`routing-jev.md`](./routing-jev.md) · Plan: [`plan-execute.md`](./plan-execute.md) · RAG ports: [`generate-and-rag-ports.md`](./generate-and-rag-ports.md) · Guard: [`guardrails.md`](./guardrails.md).

## Edges (tóm tắt)

```text
START → input_guard
input_guard → orchestrator       # allow
input_guard → END                # refuse (answer = template)

orchestrator → generate          # direct (có thể coi direct = generate luôn)
orchestrator → retrieve → rerank → generate
orchestrator → single_tool → generate
orchestrator → multi_plan → execute_plan → gather_review

gather_review → generate
gather_review → single_tool → … → gather_review | generate
gather_review → multi_plan → execute_plan → gather_review

generate → output_guard → END

(*) hết max_review_loops → generate (code ép, không gọi Jev)
```

Diagram đầy đủ: hub [`agent-architecture.md`](./agent-architecture.md).

## File dự kiến

```text
agent/nodes/
├── input_guard.py
├── orchestrator.py
├── retrieve.py
├── rerank.py
├── single_tool.py
├── multi_plan.py
├── execute_plan.py
├── gather_review.py
├── generate.py
└── output_guard.py
```

`graph.py` compile nodes + conditional edges.

## Khi đổi gì thì đụng đâu

- Thêm nhánh route → `nodes` + `graph` + `RouteDecision` + routing rubric  
- Đổi hành vi review → `gather_review` + `ReviewDecision` + budget trong graph  
- Đổi retrieve/rerank internals → `rag/` (node chỉ giữ port call)  
- Đổi rule input/output → `agent/guardrails/` (node chỉ gọi port)
