# Kiến trúc dự án

Tài liệu mô tả khung kiến trúc thư mục của `agent-ai-rag`: FastAPI + LangGraph + RAG (ingest PDF) + Auth.

## Tổng quan

```text
Client
  │
  ▼
app/ (FastAPI) ── auth / documents / chat
  │
  ├── services/ ── orchestration use-case
  │
  ├── rag/ ── ingest PDF → chunk → embed → vectorstore
  │
  └── agent/ ── LangGraph (input_guard → Jev/LLM orchestrator → direct|retrieve|tool|plan
                 → generate → output_guard; gather_review cũng Jev → LLM nếu low conf)
```

Chi tiết runtime agent (gồm **Jev + LLM fallback**): xem [`agent/agent-architecture.md`](./agent/agent-architecture.md).

Luồng chính:

1. User đăng nhập qua `app` (auth).
2. User upload PDF qua API → `services` gọi `rag/ingest`.
3. User chat → `services` gọi `agent` graph (orchestrator phân luồng qua Jev, LLM khi confidence thấp).

## Cây thư mục

```text
agent-ai-rag/
├── app/                    # FastAPI application
│   ├── api/
│   │   └── v1/             # REST endpoints theo version
│   ├── core/               # config, security, logging
│   ├── db/
│   │   └── migrations/     # schema / Alembic migrations
│   ├── schemas/            # Pydantic request/response
│   └── services/           # use-case orchestration
├── agent/                  # LangGraph domain
│   ├── nodes/              # các bước trong graph
│   ├── routing/            # Jev + LLM fallback (route / review)
│   ├── tools/              # search/, calc/, timeutil/, document/
│   └── prompts/            # prompt templates
├── rag/                    # RAG infrastructure
│   ├── ingest/             # to_markdown multi-source (pdf/md/txt/docx, …)
│   ├── retriever.py        # (sẽ có) vector search
│   └── rerank.py           # rerank candidates → top-n
├── workers/                # background jobs (ingest nặng)
├── storage/
│   └── uploads/            # file PDF tạm / local storage
├── tests/
│   ├── api/
│   ├── agent/
│   │   └── tools/
│   │       ├── search/
│   │       ├── calc/
│   │       ├── timeutil/
│   │       └── document/
│   └── rag/
└── docs/                   # tài liệu dự án
```

## Hướng dẫn từng folder

### `app/`

Lớp ứng dụng HTTP. Chịu trách nhiệm nhận request, validate, auth, trả response.

| Folder | Dùng để làm gì |
|---|---|
| `app/api/` | Định nghĩa router, deps (`Depends`), mount API |
| `app/api/v1/` | Endpoint version 1: auth, documents, chat, health |
| `app/core/` | Settings, JWT/password hashing, logging dùng chung |
| `app/db/` | Database session, SQLAlchemy models |
| `app/db/migrations/` | Migration schema (Alembic) |
| `app/schemas/` | Pydantic models: request/response DTO |
| `app/services/` | Điều phối use-case: gọi rag/agent, không chứa HTTP detail |

**Không đặt ở đây:** logic chunking PDF, wiring LangGraph nodes.

### `agent/`

Domain LangGraph: state, nodes, tools, prompts, compile graph.

| Folder | Dùng để làm gì |
|---|---|
| `agent/nodes/` | Từng bước graph: orchestrator, retrieve, rerank, tools, gather_review, generate… |
| `agent/routing/` | Jev client + LLM fallback cho route/review (xem agent-architecture) |
| `agent/tools/` | Tool theo nhóm thư mục (`search/`, `calc/`, `timeutil/`, `document/` …) |
| `agent/prompts/` | Rubric/options Jev + prompt LLM fallback / generate |

**Không đặt ở đây:** đọc JWT, nhận multipart upload, thao tác FastAPI request.

### `rag/`

Hạ tầng RAG: ingest tài liệu và retrieval.

| Folder | Dùng để làm gì |
|---|---|
| `rag/ingest/` | Pipeline: to_markdown (pdf/md/txt/docx) → chunk → embed → vector |
| `rag/` (root) | Embeddings, vectorstore client, retriever helpers |

Chi tiết thứ tự stage (upload → convert → chunk → embed → upsert): [`rag/ingest-pipeline.md`](./rag/ingest-pipeline.md).

**Không đặt ở đây:** route HTTP hay auth logic.

### `workers/`

Job nền cho tác vụ nặng/lâu (ví dụ ingest PDF lớn). API có thể trả `processing`, worker cập nhật status khi xong.

Dùng khi upload sync quá chậm; MVP có thể chưa cần implement.

### `storage/`

Lưu file vật lý (local). Production có thể thay bằng S3/MinIO nhưng vẫn giữ abstraction tương tự.

| Folder | Dùng để làm gì |
|---|---|
| `storage/uploads/` | PDF vừa upload, trước/sau khi ingest |

### `tests/`

Test theo từng lớp để giữ boundary rõ.

| Folder | Dùng để làm gì |
|---|---|
| `tests/api/` | Test endpoint FastAPI, auth, upload |
| `tests/agent/` | Test graph, routing, node behavior |
| `tests/rag/` | Test ingest, chunking, retrieve |

### `docs/`

```text
docs/
└── architecture/
    ├── architecture.md              # khung dự án (file này)
    └── agent/
        ├── agent-architecture.md    # hub runtime LangGraph
        ├── routing-jev.md
        ├── state.md
        ├── nodes.md
        ├── plan-execute.md
        ├── tools.md
        ├── generate-and-rag-ports.md
        └── guardrails.md            # input_guard + output_guard
```

## Ranh giới trách nhiệm

| Lớp | Làm | Không làm |
|---|---|---|
| `app/api` | HTTP, status code, validation | Gọi LLM trực tiếp |
| `app/services` | Use-case upload/chat/auth | Chunking / graph wiring chi tiết |
| `rag` | PDF → vectors, retrieve | Biết FastAPI request |
| `agent` | LangGraph flow | Đọc JWT / multipart file |
| `app/db` | User, Document, Conversation | Embedding logic |

## Gợi ý đặt file sau này (chưa tạo)

Khi bắt đầu code, các file then chốt thường nằm như sau:

- `app/main.py` — tạo FastAPI app
- `app/api/v1/auth.py` / `documents.py` / `chat.py` — routes
- `app/core/config.py` / `security.py` — settings & auth
- `agent/graph.py` / `state.py` / `models.py` — graph, state, ChatOpenAI factory
- `rag/ingest/pipeline.py` — orchestrate ingest PDF
- `langgraph.json` — (optional) nếu dùng LangGraph CLI/Studio
- `.env` — secrets & runtime config
