# Generate & RAG ports

Hub: [`agent-architecture.md`](./agent-architecture.md) · Nodes: [`nodes.md`](./nodes.md) · State: [`state.md`](./state.md)

## Mục đích

Chốt cách agent lấy context tài liệu và trả lời user: nodes `retrieve` / `rerank` chỉ gọi **port** vào `rag/`; `generate` luôn là LLM tổng hợp — không trả raw tool/RAG output cho client.

## Làm / không làm

| Làm | Không làm |
|---|---|
| Port `retrieve` / `rerank` ổn định | Embed / chunk / GraphRAG internals trong `agent/` |
| `generate` ghép `documents` + `tool_results` + `query` | Bypass generate để stream raw tool |
| Filter `user_id` trước retrieve | Rerank thay cho filter ownership |

## Luồng RAG trong graph

```text
query + user_id + project_id
        │
        ▼
retrieve  →  mở collection proj_{project_id}
          →  search CHILD vectors (top retrieve_k)
          →  load PARENT bằng parent_id (store riêng — Cách B)
          →  documents_candidates (+ citation meta)
        │
        ▼
rerank    →  giữ rerank_top_n (vd. 5) →  documents
        │
        ▼
generate  →  answer từ parent text
          →  (sau) kèm citation: filename + heading_path [+ link qua document_id]
```

Ingest / Qdrant / parent store — [`../rag/ingest-pipeline.md`](../rag/ingest-pipeline.md). Chunking chi tiết — [`../rag/chunking.md`](../rag/chunking.md).

| Thành phần agent | Gọi |
|---|---|
| `nodes/retrieve.py` | `rag` retriever port (child → parent_id → parent_text) |
| `nodes/rerank.py` | `rag` rerank port |
| `nodes/generate.py` | LLM + prompt generate (+ citation fields) |

Logic store/embed/rerank model thuộc `rag/` (xem khung dự án [`../architecture.md`](../architecture.md)).

## Contract port (ổn định)

```text
retrieve(query, user_id, project_id, k) → documents_candidates
rerank(query, candidates, top_n) → documents
```

Shape candidate gợi ý (sau expand):

```text
child_text: str
parent_text: str              # từ parent store
parent_id: str
heading_path: str             # citation
filename: str                 # citation
document_id: str              # join R2 / documents khi cần link
score: float | null
```

Không có `project_id` trên session → nhánh retrieve PDF project **không** chạy (default chat).

Agent **không** phụ thuộc vector vs hybrid vs GraphRAG — chỉ cần candidates/documents đúng shape cho generate.

Nâng GraphRAG sau này: đổi bên trong `rag/`, giữ contract trên → graph agent không đổi.

## Generate

**Input điển hình:** `query`, `messages` (optional), `documents` (đã có parent + citation meta), `tool_results`.  
**Output:** `answer` (string) → END; sau này có thể kèm `citations[]` structured.

Mọi nhánh (`direct`, sau tool, sau RAG, sau review) đều kết thúc bằng generate khi trả lời user.

## Config gợi ý

| Knob | Default gợi ý |
|---|---|
| `retrieve_k` | `20` |
| `rerank_top_n` | `5` |

### Rerank theo giai đoạn (trong `rag/`)

1. Stub / pass-through: giữ thứ tự score, cắt top-n  
2. Cross-encoder hoặc API (Cohere/Jina)  
3. LLM rerank nhẹ — chỉ khi chưa có model rerank riêng  

## Khi đổi gì thì đụng đâu

- Đổi thuật toán retrieve/rerank → `rag/` only  
- Đổi shape document → port + `generate` prompt + state field docs  
- Đổi giọng trả lời / citation → `prompts/generate.py`
