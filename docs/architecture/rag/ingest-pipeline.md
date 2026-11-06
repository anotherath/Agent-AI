# Ingest pipeline (PDF → vector)

Hub: [`../architecture.md`](../architecture.md) · Chunking (chi tiết): [`chunking.md`](./chunking.md) · Agent RAG ports: [`../agent/generate-and-rag-ports.md`](../agent/generate-and-rag-ports.md)

## Mục đích

Mô tả **pipeline nạp tài liệu** sau upload. **Chunking đã chốt** (heading-aware + recursive + parent–child). Model embed và vài knob vận hành vẫn mở.

## Làm / không làm

| Làm | Không làm |
|---|---|
| Thứ tự bước + status trên `documents` | Semantic / agentic / late chunking (không phải MVP) |
| Chunking: heading-aware MD + recursive token + overlap; parent–child retrieve | Cắt fixed-size thuần; dựa `pymupdf4llm.to_chunks` làm nguồn chính |
| Input/output từng stage (contract thô) | HTTP / JWT / OAuth |
| Gắn `project_id` xuyên suốt | Logic chat / LangGraph nodes |
| Check trùng nội dung để bỏ qua chunk/embed | Near-duplicate semantic (embedding similarity) — giai đoạn sau |

## Luồng tổng

```text
Client upload PDF
        │
        ▼
[1] UPLOAD + PERSIST
  → Cloudflare R2
  → Postgres `documents` (status=pending, storage_key/url, project_id, …)
        │
        ▼
[2] FETCH
  → tải bytes PDF từ R2 (temp local / stream)
  → (optional) hash file bytes = file_sha256
        │
        ▼
[2b] DEDUP FILE (optional, sớm)
  → nếu cùng project đã có document ready cùng file_sha256
  → gắn duplicate_of → status=duplicate → STOP (không convert/chunk/embed)
        │
        ▼
[3] CONVERT          ← đã có: rag/ingest/pdf_to_md.py
  → PDF → Markdown (pymupdf4llm, no OCR)
  → (optional) lưu .md phụ trên R2 / chỉ giữ in-memory cho bước sau
        │
        ▼
[4] DEDUP CONTENT    ← check trùng nội dung (hash markdown)
  → chuẩn hóa markdown nhẹ → content_sha256
  → nếu cùng project đã có document ready cùng content_sha256
  → gắn duplicate_of → status=duplicate → STOP (không chunk/embed/upsert)
        │
        ▼
[5] CHUNK            ← đã chốt: heading-aware + recursive + parent–child
  → Markdown → sections (parent) → child chunks (embed unit)
  → lưu PARENT store riêng; child chỉ giữ parent_id (+ citation meta)
        │
        ▼
[6] EMBED            ← chưa chốt model (gợi ý: text-embedding-3-small)
  → embed **child** text (+ optional heading_path prefix) → vectors
        │
        ▼
[7] UPSERT
  → Qdrant **1 collection / project** (vd. `proj_{project_id}`)
  → payload child: text, parent_id, citation fields, ids …
  → parent_text **không** nhét vào payload (Cách B)
        │
        ▼
[8] FINALIZE
  → documents.status = ready | failed | duplicate
  → chunk_count / error / duplicate_of / finished_at
```

**Retrieve lúc chat** không nằm trong pipeline này — xem port `retrieve` / `rerank` bên agent.

Document `duplicate` **không** có vector riêng; retrieve chỉ cần bản `ready` gốc (`duplicate_of`). Library UI vẫn hiện file vừa upload, có thể badge “trùng nội dung”.

## Status `documents` (gợi ý)

| Status | Nghĩa |
|---|---|
| `pending` | Đã có trên R2 + row DB; chưa / đang chờ xử lý |
| `processing` | Đang convert → dedup → chunk → embed → upsert |
| `ready` | Có vector, dùng được cho retrieve |
| `duplicate` | Nội dung (hoặc file) trùng document khác trong cùng project; bỏ qua pipeline nặng |
| `failed` | Lỗi ở bất kỳ stage; giữ `error` message |

## Chi tiết từng stage

### 1. Upload + persist

| | |
|---|---|
| **Input** | file PDF, `user_id`, `project_id` |
| **Output** | `document_id`, `storage_key` / URL R2, `status=pending` |
| **Chỗ** | `app/services` + storage client R2 + DB |
| **Ghi chú** | API có thể trả `pending` ngay; ingest chạy sync ngắn hoặc `workers/` |

### 2. Fetch

| | |
|---|---|
| **Input** | `storage_key` |
| **Output** | path tạm hoặc bytes PDF; optional `file_sha256` |
| **Chỗ** | `rag/ingest` (hoặc storage helper dùng chung) |

### 2b. Dedup file *(optional)*

| | |
|---|---|
| **Input** | `file_sha256`, `project_id` |
| **Output** | `hit: document_id` hoặc miss |
| **Chỗ dự kiến** | `rag/ingest/dedup.py` + lookup DB |
| **Ghi chú** | Bắt file upload y hệt (byte-identical). Rẻ, làm trước convert. |

### 3. Convert

| | |
|---|---|
| **Input** | PDF path / bytes |
| **Output** | Markdown string (+ optional path `.md`) |
| **Chỗ** | `rag/ingest/pdf_to_md.py` (**đã có**) |
| **Ghi chú** | Text layer only; scan/OCR = giai đoạn sau |

### 4. Dedup content *(nội dung trùng)*

| | |
|---|---|
| **Input** | Markdown, `project_id`, `document_id` |
| **Output** | `DedupResult(is_duplicate, duplicate_of?, content_sha256)` |
| **Chỗ dự kiến** | `rag/ingest/dedup.py` — `content_fingerprint(markdown)` + `find_duplicate(...)` |

**Cách làm (MVP):**

1. Normalize markdown nhẹ: strip, thống nhất `\n`, có thể collapse khoảng trắng thừa  
2. `content_sha256 = sha256(normalized_utf8)`  
3. Tra DB trong **cùng `project_id`**: đã có row `status=ready` (hoặc `duplicate` trỏ về ready) với cùng `content_sha256`?  
4. Hit → set `duplicate_of = <id gốc>`, `status=duplicate`, **return sớm**  
5. Miss → lưu `content_sha256` trên document hiện tại → tiếp tục chunk  

**Phạm vi trùng:** theo **project** (hai project khác nhau vẫn ingest riêng — kho PDF/vector tách).

**Không làm ở MVP:** so khớp “gần giống” bằng embedding cosine — đắt và phức tạp hơn hash.

**Cột DB gợi ý trên `documents`:**

```text
file_sha256        text nullable
content_sha256     text nullable
duplicate_of       UUID FK → documents.id nullable
```

Index: `(project_id, content_sha256)`, `(project_id, file_sha256)`.

### 5. Chunk *(đã chốt)*

**Tên kỹ thuật:** Heading-aware Markdown chunking + recursive token split (có overlap) + **parent–child** retrieval (small-to-big).

**Chi tiết đầy đủ (ví dụ, edge cases, pseudo-code, so sánh kỹ thuật):** [`chunking.md`](./chunking.md).

| | |
|---|---|
| **Input** | Markdown (+ metadata document/project) |
| **Output** | `parents[]` + `children[]` (embed unit = child) |
| **Chỗ dự kiến** | `rag/ingest/chunking.py` |

```text
Markdown → split heading → PARENT sections
         → recursive + overlap nếu dài → CHILD chunks
Persist: ParentRecord (store riêng, Cách B) + child → Qdrant
Chat:    search child → load parent_id → generate (+ citation)
```

| Tầng | Vai trò |
|---|---|
| **Child** | Embed + vector search; payload có `parent_id`, `filename`, `heading_path` |
| **Parent** | Store riêng → expand sau retrieve |

Knob / contract / citation / Cách B: xem [`chunking.md`](./chunking.md). Port retrieve: [`../agent/generate-and-rag-ports.md`](../agent/generate-and-rag-ports.md).

### 6. Embed *(chưa chốt)*

| | |
|---|---|
| **Input** | `list[Chunk]` |
| **Output** | `list[{chunk, vector}]` |
| **Chỗ dự kiến** | `rag/embeddings.py` |

**Ứng viên:** OpenAI embeddings / model local / provider khác — chọn khi có cost/latency target.

### 7. Upsert vectorstore *(đã chốt scope)*

| | |
|---|---|
| **Input** | child vectors + payload (không có `parent_text`) + ParentRecords |
| **Output** | point ids / count; parents đã persist |
| **Chỗ dự kiến** | `rag/vectorstore.py` (Qdrant) + parent store (Postgres) |
| **Scope** | **1 collection / project** — tên gợi ý `proj_{project_id}` |

Tạo collection khi project được tạo (hoặc lazy lúc ingest đầu). Xóa project → xóa collection + rows parent/document liên quan.

Không dùng 1 collection chung cả app + filter `project_id` (đã bỏ phương án này).

### 8. Finalize

| | |
|---|---|
| **Input** | success / duplicate / exception |
| **Output** | `documents.status`, `chunk_count`, `duplicate_of`, `error` |
| **Chỗ** | orchestrator ingest (`rag/ingest/pipeline.py`) gọi ngược DB qua port/service |

## Cây file dự kiến (chưa code hết)

```text
rag/
├── __init__.py
├── ingest/
│   ├── __init__.py
│   ├── pdf_to_md.py          # ✅ convert
│   ├── dedup.py              # ⏳ fingerprint + check trùng
│   ├── chunking.py           # ⏳ heading + recursive; emit children + parents
│   ├── pipeline.py           # ⏳ orchestration 2→8
│   └── types.py              # ⏳ Chunk, ParentRecord, DedupResult, …
├── embeddings.py             # ⏳
├── vectorstore.py            # ⏳ Qdrant: 1 collection / project
├── parents.py                # ⏳ (optional) CRUD ParentRecord
├── retriever.py              # ⏳ child search → load parent → citation fields
└── rerank.py                 # ⏳ (chat path)
```

`app/services` chỉ: upload R2 → insert DB → gọi `pipeline.run(document_id)` (hoặc enqueue worker).

## Metadata: embed vs payload vs DB

| Chỗ | Giữ gì |
|---|---|
| **Embed (vector)** | Child `text` (+ optional `heading_path` prefix) |
| **Qdrant payload** | `project_id`, `document_id`, `chunk_index`, `text`, `parent_id`, `heading_path`, `filename`, `source_type`, … |
| **Parent store** | `parent_id` → `parent_text` + `heading_path` + ids |
| **Postgres `documents`** | R2 key, status, hashes, dedup, filename, … — nguồn link file cho citation |

## Orchestrator `pipeline.run` (pseudo)

```text
load document row (must pending|retry)
set status=processing
pdf_bytes = fetch from R2
file_sha256 = sha256(pdf_bytes)

if find_duplicate(project_id, file_sha256=file_sha256):
    set duplicate_of, status=duplicate → return

markdown = convert(pdf)
content_sha256 = content_fingerprint(markdown)

if find_duplicate(project_id, content_sha256=content_sha256):
    set duplicate_of, status=duplicate → return

save content_sha256 (+ file_sha256) on document
ensure_collection(proj_{project_id})

parents, children = chunk_heading_recursive(markdown, meta)
save_parents(parents)                 # Cách B
vectors = embed(child.text for child in children)
upsert_children(collection, vectors, child payloads)  # payload có parent_id, filename, heading_path
set status=ready, chunk_count=N
on error → status=failed, error=...
```

## Quyết định đã chốt

| Mục | Chốt |
|---|---|
| Chunk strategy | Heading-aware MD + recursive token split + overlap |
| Retrieve shape | Parent–child (search child → load parent → generate) |
| Parent storage | **Cách B** — `parent_id` + store/bảng riêng (không `parent_text` trong payload) |
| Qdrant scope | **1 collection / project** (`proj_{project_id}`) |
| Citation | Payload có `filename` + `heading_path` + `document_id`; URL/R2 qua `documents` khi cần |
| Dedup | Exact hash file (optional) + content hash sau convert, theo project |

## Phụ thuộc / quyết định còn mở

| # | Câu hỏi | Ảnh hưởng |
|---|---|---|
| 1 | Exact `max_tokens` / overlap / parent cap | knob `chunking.py` |
| 2 | Embedding model + dim | `embeddings.py`, Qdrant schema |
| 3 | Ingest sync trong request vs `workers/` | API UX, timeout |
| 4 | Có lưu `.md` lên R2 sau convert không | storage cost / debug |
| 5 | Xử lý PDF scan / OCR sau này thế nào | convert stage |
| 6 | Dedup chỉ exact hash hay thêm near-dup sau? | `dedup.py` |
| 7 | Upload trùng: giữ file R2 mới hay xóa / reuse storage gốc? | storage cost |
| 8 | `page_start` / `page_end` trên citation khi nào thêm | convert/chunk metadata |

## Khi đổi gì thì đụng đâu

| Đổi | Đụng |
|---|---|
| Cách convert PDF | `pdf_to_md.py` only |
| Cách fingerprint / dedup | `dedup.py` + cột hash trên `documents` |
| Cách cắt chunk / parent store | `chunking.py` + `parents` store + retriever expand |
| Model embed | `embeddings.py` (+ dim Qdrant nếu đổi) |
| Qdrant layout / collection naming | `vectorstore.py` + tạo/xóa theo project |
| Citation fields | payload + generate prompt + (sau) UI |
| Thứ tự stage | `pipeline.py` |
| Upload/auth | `app/` — không nhét vào `rag/ingest` |
