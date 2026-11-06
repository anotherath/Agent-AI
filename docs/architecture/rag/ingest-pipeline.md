# Ingest pipeline (document → vector)

Hub: [`../architecture.md`](../architecture.md) · Chunking (chi tiết): [`chunking.md`](./chunking.md) · Agent RAG ports: [`../agent/generate-and-rag-ports.md`](../agent/generate-and-rag-ports.md)

## Mục đích

Mô tả **pipeline nạp tài liệu** sau upload. **Chunking đã chốt** (heading-aware + recursive + parent–child). Input không chỉ PDF: hỗ trợ thêm **Markdown sẵn**, **plain text (`.txt`)**, và **file docs** (vd. `.docx`). Model embed và vài knob vận hành vẫn mở. **Chưa triển khai code** cho nhánh MD/TXT/DOCX — chỉ chốt trong doc này.

## Làm / không làm

| Làm | Không làm |
|---|---|
| Thứ tự bước + status trên `documents` | Semantic / agentic / late chunking (không phải MVP) |
| Multi-source: PDF, `.md` sẵn, `.txt`, docs (`.docx`) → cùng pipeline sau khi có Markdown | OCR / scan PDF; `.doc` legacy; mọi định dạng office khác ở MVP |
| Chunking: heading-aware MD + recursive token + overlap; parent–child retrieve | Cắt fixed-size thuần; dựa `pymupdf4llm.to_chunks` làm nguồn chính |
| Input/output từng stage (contract thô) | HTTP / JWT / OAuth |
| Gắn `project_id` xuyên suốt | Logic chat / LangGraph nodes |
| Check trùng nội dung để bỏ qua chunk/embed | Near-duplicate semantic (embedding similarity) — giai đoạn sau |

## Source types (MVP)

| `source_type` | Extension | Convert? | Ghi chú |
|---|---|---|---|
| `pdf` | `.pdf` | Có — `pdf_to_md.py` (**đã có**) | Text layer only; no OCR |
| `markdown` | `.md` | **Không** — đọc UTF-8 → Markdown string | Skip convert; đi thẳng dedup content |
| `text` | `.txt` | **Không** — đọc UTF-8 → plain text (xem như MD không heading) | Skip convert; chunk fallback recursive (ít/không có `#` heading) |
| `docx` | `.docx` | Có — converter riêng (**chưa code**) | Docs/Word → Markdown; lib cụ thể còn mở |

Sau khi có Markdown (dù convert hay load sẵn), các stage **4 → 8 giống nhau**. Payload / DB nên lưu `source_type` + `filename` để citation và debug.

Reject sớm ở upload nếu extension không thuộc bảng trên (hoặc map MIME → `source_type`).

## Luồng tổng

```text
Client upload file (PDF | .md | .txt | .docx)
        │
        ▼
[1] UPLOAD + PERSIST
  → Cloudflare R2
  → Postgres `documents` (status=pending, storage_key/url, project_id,
                          source_type, filename, …)
        │
        ▼
[2] FETCH
  → tải bytes từ R2 (temp local / stream)
  → (optional) hash file bytes = file_sha256
        │
        ▼
[2b] DEDUP FILE (optional, sớm)
  → nếu cùng project đã có document ready cùng file_sha256
  → gắn duplicate_of → status=duplicate → STOP (không convert/chunk/embed)
        │
        ▼
[3] TO MARKDOWN          ← nhánh theo source_type
  → pdf:      PDF → Markdown (pymupdf4llm)     [pdf_to_md.py ✅]
  → markdown: đọc .md UTF-8 → Markdown        [skip convert]
  → text:     đọc .txt UTF-8 → plain text     [skip convert]
  → docx:     DOCX → Markdown                 [docx_to_md.py ⏳]
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
  → payload child: text, parent_id, citation fields, ids, source_type …
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
| `processing` | Đang to-markdown → dedup → chunk → embed → upsert |
| `ready` | Có vector, dùng được cho retrieve |
| `duplicate` | Nội dung (hoặc file) trùng document khác trong cùng project; bỏ qua pipeline nặng |
| `failed` | Lỗi ở bất kỳ stage; giữ `error` message |

## Chi tiết từng stage

### 1. Upload + persist

| | |
|---|---|
| **Input** | file (`pdf` \| `md` \| `txt` \| `docx`), `user_id`, `project_id` |
| **Output** | `document_id`, `storage_key` / URL R2, `status=pending`, `source_type` |
| **Chỗ** | `app/services` + storage client R2 + DB |
| **Ghi chú** | API có thể trả `pending` ngay; ingest chạy sync ngắn hoặc `workers/`. Validate extension/MIME → set `source_type`. Reject type ngoài MVP. |

### 2. Fetch

| | |
|---|---|
| **Input** | `storage_key` |
| **Output** | path tạm hoặc bytes (PDF / MD / TXT / DOCX); optional `file_sha256` |
| **Chỗ** | `rag/ingest` (hoặc storage helper dùng chung) |

### 2b. Dedup file *(optional)*

| | |
|---|---|
| **Input** | `file_sha256`, `project_id` |
| **Output** | `hit: document_id` hoặc miss |
| **Chỗ dự kiến** | `rag/ingest/dedup.py` + lookup DB |
| **Ghi chú** | Bắt file upload y hệt (byte-identical), **mọi** `source_type`. Rẻ, làm trước to-markdown. |

### 3. To Markdown *(nhánh theo `source_type`)*

| | |
|---|---|
| **Input** | path / bytes + `source_type` |
| **Output** | Markdown string (+ optional path `.md` phụ) |
| **Chỗ** | dispatcher trong `pipeline.py` + converter theo type |

| `source_type` | Hành vi | Module |
|---|---|---|
| `pdf` | PDF → MD (text layer) | `rag/ingest/pdf_to_md.py` ✅ |
| `markdown` | Decode UTF-8 (optional strip BOM); **không** convert | `load_text.py` (chung với txt) ⏳ |
| `text` | Decode UTF-8 (optional strip BOM); **không** convert; coi như MD phẳng | `load_text.py` ⏳ |
| `docx` | DOCX → MD | `rag/ingest/docx_to_md.py` ⏳ |

**Ghi chú:**

- Chunking chỉ cần Markdown (hoặc text tương thích) — mọi format hội tụ tại đây.
- PDF: scan/OCR = giai đoạn sau.
- DOCX: giữ heading/structure càng gần MD càng tốt (để heading-aware chunk ăn được); bảng/ảnh phức tạp = best-effort MVP.
- `.md` sẵn: nếu user upload MD “bẩn” (HTML lẫn, encoding lạ) → normalize nhẹ ở dedup; không parse HTML full ở MVP.
- `.txt`: thường **không có heading** `#` → stage chunk vẫn chạy heading-aware nhưng thường ra **1 parent lớn** rồi recursive + overlap cắt child; không cần pipeline chunk riêng ở MVP.

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

**Phạm vi trùng:** theo **project** (hai project khác nhau vẫn ingest riêng — kho file/vector tách). Trùng **xuyên format** vẫn bắt được nếu cùng nội dung Markdown sau convert (vd. PDF và `.md` cùng text → cùng `content_sha256`).

**Không làm ở MVP:** so khớp “gần giống” bằng embedding cosine — đắt và phức tạp hơn hash.

**Cột DB gợi ý trên `documents`:**

```text
source_type        text not null   -- pdf | markdown | text | docx
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
| **Child** | Embed + vector search; payload có `parent_id`, `filename`, `heading_path`, `source_type` |
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
│   ├── pdf_to_md.py          # ✅ convert PDF
│   ├── docx_to_md.py         # ⏳ convert DOCX (docs)
│   ├── load_text.py          # ⏳ đọc .md / .txt UTF-8 → string
│   ├── dedup.py              # ⏳ fingerprint + check trùng
│   ├── chunking.py           # ⏳ heading + recursive; emit children + parents
│   ├── pipeline.py           # ⏳ orchestration 2→8; dispatch source_type ở stage 3
│   └── types.py              # ⏳ Chunk, ParentRecord, DedupResult, SourceType, …
├── embeddings.py             # ⏳
├── vectorstore.py            # ⏳ Qdrant: 1 collection / project
├── parents.py                # ⏳ (optional) CRUD ParentRecord
├── retriever.py              # ⏳ child search → load parent → citation fields
└── rerank.py                 # ⏳ (chat path)
```

`app/services` chỉ: upload R2 → insert DB (`source_type`) → gọi `pipeline.run(document_id)` (hoặc enqueue worker).

## Metadata: embed vs payload vs DB

| Chỗ | Giữ gì |
|---|---|
| **Embed (vector)** | Child `text` (+ optional `heading_path` prefix) |
| **Qdrant payload** | `project_id`, `document_id`, `chunk_index`, `text`, `parent_id`, `heading_path`, `filename`, `source_type`, … |
| **Parent store** | `parent_id` → `parent_text` + `heading_path` + ids |
| **Postgres `documents`** | R2 key, status, hashes, dedup, filename, `source_type`, … — nguồn link file cho citation |

## Orchestrator `pipeline.run` (pseudo)

```text
load document row (must pending|retry)
set status=processing
file_bytes = fetch from R2
file_sha256 = sha256(file_bytes)

if find_duplicate(project_id, file_sha256=file_sha256):
    set duplicate_of, status=duplicate → return

# --- stage 3: hội tụ về Markdown ---
match document.source_type:
  pdf:
    markdown = convert_pdf(file_bytes)          # pdf_to_md
  markdown | text:
    markdown = decode_utf8(file_bytes)          # load_text; skip convert
  docx:
    markdown = convert_docx(file_bytes)         # docx_to_md (chưa code)
  else:
    fail unsupported source_type

content_sha256 = content_fingerprint(markdown)

if find_duplicate(project_id, content_sha256=content_sha256):
    set duplicate_of, status=duplicate → return

save content_sha256 (+ file_sha256) on document
ensure_collection(proj_{project_id})

parents, children = chunk_heading_recursive(markdown, meta)
save_parents(parents)                 # Cách B
vectors = embed(child.text for child in children)
upsert_children(collection, vectors, child payloads)
  # payload có parent_id, filename, heading_path, source_type
set status=ready, chunk_count=N
on error → status=failed, error=...
```

## Quyết định đã chốt

| Mục | Chốt |
|---|---|
| Input MVP | **PDF + `.md` sẵn + `.txt` + `.docx`** (hội tụ Markdown/text ở stage 3) |
| Chunk strategy | Heading-aware MD + recursive token split + overlap |
| Retrieve shape | Parent–child (search child → load parent → generate) |
| Parent storage | **Cách B** — `parent_id` + store/bảng riêng (không `parent_text` trong payload) |
| Qdrant scope | **1 collection / project** (`proj_{project_id}`) |
| Citation | Payload có `filename` + `heading_path` + `document_id` + `source_type`; URL/R2 qua `documents` khi cần |
| Dedup | Exact hash file (optional) + content hash sau khi có Markdown, theo project (xuyên format) |

## Phụ thuộc / quyết định còn mở

| # | Câu hỏi | Ảnh hưởng |
|---|---|---|
| 1 | Exact `max_tokens` / overlap / parent cap | knob `chunking.py` |
| 2 | Embedding model + dim | `embeddings.py`, Qdrant schema |
| 3 | Ingest sync trong request vs `workers/` | API UX, timeout |
| 4 | Có lưu `.md` lên R2 sau convert (PDF/DOCX) không | storage cost / debug |
| 5 | Xử lý PDF scan / OCR sau này thế nào | convert PDF |
| 6 | Dedup chỉ exact hash hay thêm near-dup sau? | `dedup.py` |
| 7 | Upload trùng: giữ file R2 mới hay xóa / reuse storage gốc? | storage cost |
| 8 | `page_start` / `page_end` trên citation khi nào thêm | convert/chunk metadata (chủ yếu PDF) |
| 9 | Lib DOCX → MD nào (pandoc, python-docx, markitdown, …) | `docx_to_md.py` |
| 10 | Có nhận `.html` (và CSV/JSON) sau này không | upload validation + dispatcher |

## Khi đổi gì thì đụng đâu

| Đổi | Đụng |
|---|---|
| Cách convert PDF | `pdf_to_md.py` only |
| Cách convert DOCX | `docx_to_md.py` (+ deps) |
| Load `.md` / `.txt` | `load_text.py` / nhánh trong `pipeline.py` |
| Thêm source type mới | upload validation + dispatcher stage 3 + cột/`source_type` |
| Cách fingerprint / dedup | `dedup.py` + cột hash trên `documents` |
| Cách cắt chunk / parent store | `chunking.py` + `parents` store + retriever expand |
| Model embed | `embeddings.py` (+ dim Qdrant nếu đổi) |
| Qdrant layout / collection naming | `vectorstore.py` + tạo/xóa theo project |
| Citation fields | payload + generate prompt + (sau) UI |
| Thứ tự stage | `pipeline.py` |
| Upload/auth | `app/` — không nhét vào `rag/ingest` |
