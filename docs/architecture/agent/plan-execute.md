# Multi-plan, execute & review budget

Hub: [`agent-architecture.md`](./agent-architecture.md) · Nodes: [`nodes.md`](./nodes.md) · Tools: [`tools.md`](./tools.md)

## Mục đích

Chạy chuỗi tool có phụ thuộc (output bước trước → input bước sau) bằng **plan list cứng**, không để LLM gọi tool loạn. Sau execute: `gather_review` (Jev→LLM) quyết định tiếp hoặc generate.

## Làm / không làm

| Làm | Không làm |
|---|---|
| `multi_plan` → `plan[]` schema | Nhét dependency vào `single_tool` |
| `execute_plan` tuần tự + resolve `$stepN` | Orchestrator gọi song song bước phụ thuộc |
| `gather_review` + `max_review_loops` | Bắt user gọi từng tool thủ công |
| Append `tool_results` mỗi bước | Gộp nhiều dependency thành một “super tool” |

## Khi nào vào nhánh này

Chỉ khi orchestrator chọn `multi_plan` (hoặc gather_review chọn `multi_plan` lại). Case 1 tool → `single_tool`.

## Cơ chế

1. Plan có **thứ tự** rõ (`PlanStep[]`).
2. Mỗi bước xong → append `tool_results[]`: `{step, tool, args, result, ok}`.
3. Trước bước kế, `execute_plan` **resolve** `tool_args` chứa reference tới bước trước rồi `tool.invoke(...)`.

## Bind args

| Cách | Khi nào |
|---|---|
| **`$stepN.path`** | Schema ổn định — ưu tiên |
| **LLM điền args từng bước** | Result lệch schema / khó map cứng |

### Ví dụ

```text
step0: time_shift(days=-7)
       → result.coingecko_date = "01-11-2026"

step1: coingecko_history(
         coin="bitcoin",
         date="$step0.result.coingecko_date"
       )

step2: coingecko_price(coin="bitcoin")

step3: calc_percent_change(
         old="$step1.result.market_data.current_price.usd",
         new="$step2.result.price.usd"
       )
```

## gather_review sau execute

Classifier: xem [`routing-jev.md`](./routing-jev.md). Schema: [`state.md`](./state.md) (`ReviewDecision`).

| Quyết định | Hành động |
|---|---|
| Đủ | → `generate` |
| Thiếu 1 thứ | → `single_tool` (args chi tiết không nhét hết vào Choice) |
| Thiếu nhiều | → `multi_plan` lại |
| Hết `max_review_loops` | → `generate` (**code ép**, không gọi Jev) |

**Budget gợi ý:** `max_review_loops = 2` (hoặc 2–3).

## Luồng ví dụ

`BTC tăng bao nhiêu % so với 7 ngày trước?`

1. orchestrator → `multi_plan`  
2. plan: time → coingecko history/price → calc %  
3. `execute_plan`  
4. `gather_review` → đủ → `generate` → END  

## Khi đổi gì thì đụng đâu

- Đổi cú pháp `$stepN` → `execute_plan` + doc này + tests  
- Đổi budget review → state default + graph guard  
- Thêm tool vào plan → registry [`tools.md`](./tools.md) + mô tả cho `multi_plan` prompt
