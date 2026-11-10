# Guardrails (input + output)

Hub: [`agent-architecture.md`](./agent-architecture.md) · Nodes: [`nodes.md`](./nodes.md) · State: [`state.md`](./state.md)

## Phạm vi (đã chốt)

Hai node trên graph:

| Node | Vị trí | Việc |
|---|---|---|
| `input_guard` | Ngay sau START | Kiểm tra `query` trước khi vào orchestrator |
| `output_guard` | Ngay sau `generate`, trước END | Kiểm tra `answer` trước khi trả user |

Không có tool-policy node riêng trong phạm vi này.

## Hành vi

### `input_guard`

- **allow** → `orchestrator`
- **refuse** → ghi `answer` = template từ chối → **END**  
  (không qua `generate` / `output_guard`)

### `output_guard`

- **allow** → END (giữ `answer`)
- **rewrite** / **strip** → sửa `answer` rồi END
- **refuse** → thay `answer` bằng template từ chối rồi END

## GuardDecision

```text
allowed: bool
action: allow | refuse | rewrite | strip
stage: input | output
reason: str
decided_by: rules | moderation | llm
```

State: field `guard: GuardDecision | null` — xem [`state.md`](./state.md).

## Code dự kiến

```text
agent/guardrails/
├── __init__.py
├── types.py           # GuardDecision
├── input_check.py     # check_input(query, …)
└── output_check.py    # check_output(answer, …)

agent/nodes/
├── input_guard.py
└── output_guard.py
```

Node chỉ gọi port; rule/moderation nằm trong `agent/guardrails/`. MVP có thể là rules; sau đổi impl mà graph không đổi.

## Khi đổi gì thì đụng đâu

- Đổi rule input/output → `agent/guardrails/` + tests  
- Đổi edge allow/refuse → `graph.py` + [`nodes.md`](./nodes.md)  
- Đổi schema quyết định → `types` / `state` + nodes guard  
