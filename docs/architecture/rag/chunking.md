# Chunking: heading-aware + recursive + parent–child

Hub pipeline: [`ingest-pipeline.md`](./ingest-pipeline.md) · Retrieve ports: [`../agent/generate-and-rag-ports.md`](../agent/generate-and-rag-ports.md)

## Mục đích

Giải thích chi tiết kỹ thuật chunking đã chốt cho đồ án: sau bước **PDF → Markdown**, cắt văn bản thế nào, lưu gì, và retrieve dùng ra sao.

**Một câu:** Chunk Markdown theo heading, section dài thì recursive token split có overlap; embed **child**, lúc chat expand **parent** (small-to-big); parent text lưu store riêng (Cách B).

## Vì sao không fixed-size thuần?

| Fixed-size | Heading-aware + recursive |
|---|---|
| Cắt giữa mục / bảng / ý đang dở | Ranh giới theo cấu trúc MD từ PDF |
| Khó citation (“đoạn nào?”) | Có `heading_path` rõ |
| Một vector chứa nhiều chủ đề | Child nhỏ → search sắc hơn |

PDF đã qua `pymupdf4llm.to_markdown` → nguồn chunk là **Markdown có heading**, tận dụng cấu trúc đó thay vì bỏ đi.

## Tổng quan 3 lớp kỹ thuật

```text
┌─────────────────────────────────────────────────────────┐
│ 1. Heading-aware split                                  │
│    MD → list[Section] = PARENT candidates               │
└───────────────────────────┬─────────────────────────────┘
                            │ section quá dài?
                            ▼
┌─────────────────────────────────────────────────────────┐
│ 2. Recursive token split + overlap                      │
│    Section → list[Child] (đơn vị embed)                 │
└───────────────────────────┬─────────────────────────────┘
                            │ ingest xong
                            ▼
┌─────────────────────────────────────────────────────────┐
│ 3. Parent–child retrieval (lúc chat)                    │
│    search Child → load Parent bằng parent_id → generate │
└─────────────────────────────────────────────────────────┘
```

Ingest chỉ làm (1)+(2) và persist. Bước (3) thuộc `retriever` / agent graph.

---

## 1. Heading-aware split

### Ý tưởng

Coi dòng heading Markdown (`#`, `##`, `###`, …) là biên section. Mỗi section gồm:

- Dòng heading (nếu có)
- Mọi nội dung cho đến heading cùng cấp hoặc cao hơn tiếp theo

### Ví dụ input

```markdown
# Chương 1 Giới thiệu

Mở đầu chương 1.

## 1.1 Mục tiêu

Chi tiết mục tiêu A.
Chi tiết mục tiêu B.

## 1.2 Phạm vi

Nội dung phạm vi.

# Chương 2 Phương pháp

Nội dung phương pháp.
```

### Kết quả section (PARENT candidates)

| parent_id (ví dụ) | heading_path | Nội dung (rút gọn) |
|---|---|---|
| `doc::s0` | `Chương 1 Giới thiệu` | mở đầu chương 1 |
| `doc::s1` | `Chương 1 Giới thiệu > 1.1 Mục tiêu` | mục tiêu A + B |
| `doc::s2` | `Chương 1 Giới thiệu > 1.2 Phạm vi` | phạm vi |
| `doc::s3` | `Chương 2 Phương pháp` | phương pháp |

`heading_path` dựng bằng stack heading theo level (vào `#` reset sâu hơn; vào `##` dưới `#` hiện tại, v.v.).

### Quy ước level

| Knob | Giá trị gợi ý |
|---|---|
| Levels tham gia split | `#` … `###` |
| `####` trở xuống | Có thể **không** tạo parent mới — gộp vào section cha (tránh mảnh quá nhỏ) |

### Edge cases

| Tình huống | Xử lý gợi ý |
|---|---|
| MD không có heading | Một parent “ảo” `"(document)"` = cả file, rồi recursive |
| Preamble trước heading đầu | Parent `"(intro)"` hoặc gắn vào section đầu |
| Heading rỗng / chỉ `#` | Vẫn tạo section; path dùng fallback `"Section {i}"` |
| Bảng / code fence | Giữ nguyên trong section; recursive **ưu tiên không cắt giữa fence** nếu làm được |

---

## 2. Recursive token split + overlap

### Khi nào chạy?

Chỉ khi `token_count(section) > child_max_tokens` (vd. 512–1024).  
Section ngắn → **một child = gần như cả parent** (vẫn có `parent_id`).

### Thứ tự ưu tiên cắt (recursive)

Cố tách tại biên “đẹp” trước; chỉ xuống cấp thấp hơn nếu mảnh vẫn quá dài:

```text
1. \n\n          (đoạn văn)
2. \n            (dòng)
3. ". " / "? "   (câu — tùy tokenizer/locale)
4. " "           (từ)
5. ký tự         (phương án cuối)
```

Đây là cùng họ ý tưởng với *recursive character text splitter*, nhưng đo bằng **token** (khớp cửa sổ embed).

### Overlap

Chunk sau lấy lại đuôi chunk trước ~**10–15%** (`64`–`128` token).

```text
[========== child 0 ==========|ov]
                      [ov|========== child 1 ==========|ov]
                                              [ov|=== child 2 ===]
```

**Mục đích:** ý / câu bị cắt ở biên vẫn xuất hiện đủ trong ít nhất một child → giảm miss retrieve.

### Đếm token

Dùng tokenizer gần với model embed (vd. tiktoken `cl100k_base` nếu OpenAI embeddings). Quan trọng hơn “chính xác tuyệt đối” là **nhất quán** lúc ingest và lúc ước lượng.

### Ví dụ

Section `1.1 Mục tiêu` = 2000 token, `max_tokens=800`, `overlap=100`:

```text
parent  doc::s1  (full section text lưu ParentRecord)
child0  tokens ~800  parent_id=doc::s1
child1  tokens ~800  overlap với đuôi child0
child2  phần còn lại
```

---

## 3. Parent–child retrieval (small-to-big)

### Vấn đề

- Embed cả section dài → vector “loãng”, nhiều chủ đề.  
- Chỉ đưa child ngắn vào LLM → thiếu ngữ cảnh, trả lời cụt.

### Cách làm

| Tầng | Lúc ingest | Lúc chat |
|---|---|---|
| **Child** | Embed + upsert Qdrant | Vector search top-k |
| **Parent** | Lưu store riêng (Cách B) | Load bằng `parent_id` → nhét vào generate |

```text
User: "Mục tiêu dự án là gì?"
        │
        ▼
Embed query → search trong collection proj_{id}
        │
        ▼
Hit child (đoạn trong ## 1.1)
        │
        ▼
parent_id → ParentRecord.parent_text  (= cả ## 1.1)
        │
        ▼
(Rerank optional) → generate(context=parent_text, …)
        │
        ▼
Answer + citation (filename, heading_path)
```

Nhiều child cùng `parent_id` trong top-k → **dedupe parent** trước khi đưa vào prompt (tránh lặp section).

---

## 4. Cách B — lưu parent riêng

### Không làm (Cách A)

Nhồi `parent_text` vào mọi Qdrant payload → đơn giản nhưng **lặp storage** khi một section có nhiều child.

### Làm (Cách B — đã chốt)

```text
Postgres (vd. chunk_parents)          Qdrant point (child)
─────────────────────────          ────────────────────────
parent_id (PK)                     vector = embed(child text)
document_id                        payload:
project_id                           text, parent_id,
heading_path                         heading_path, filename,
parent_text                          document_id, project_id,
heading_level                        chunk_index, source_type, …
token_count
```

### `parent_id` gợi ý

```text
{document_id}::s{section_index}
```

Ổn định trong một lần ingest; re-ingest document → xóa parents/children cũ của `document_id` rồi ghi lại.

---

## 5. Embed gì? Metadata nào?

### Đưa vào vector (semantic)

```text
embed_input = heading_path + "\n\n" + child_text
# hoặc chỉ child_text nếu muốn thử A/B
```

**Không** nhồi vào chuỗi embed: UUID, URL R2, hash, email, status.

### Qdrant payload (filter + citation + join)

| Field | Việc |
|---|---|
| `text` | child (debug / fallback) |
| `parent_id` | load parent |
| `document_id` | xóa theo file; join R2 |
| `project_id` | redundancy / audit (collection đã theo project) |
| `chunk_index` | thứ tự |
| `heading_path` | citation |
| `filename` | citation |
| `source_type` | `pdf` \| `memory_md` |
| (sau) `page_start`, `page_end` | citation trang |

### Citation

Generate / UI có thể nói:

> … *Nguồn: `bao-cao.pdf` — Chương 1 > 1.1 Mục tiêu*

Link mở file: `document_id` → `documents.storage_key` (R2), không bắt buộc URL trong mọi payload.

---

## 6. Qdrant & collection

Đã chốt: **1 collection / project**, tên gợi ý `proj_{project_id}`.

- Ingest / retrieve luôn gắn đúng collection của project.  
- Session không có `project_id` → không retrieve kho PDF project.  
- Xóa project → xóa collection + `chunk_parents` + documents liên quan.

Chi tiết pipeline: [`ingest-pipeline.md`](./ingest-pipeline.md).

---

## 7. Knob (điểm xuất phát)

| Knob | Gợi ý | Ghi chú |
|---|---|---|
| `heading_levels` | 1–3 (`#`…`###`) | |
| `child_max_tokens` | 512–1024 | Khớp embed model |
| `chunk_overlap_tokens` | 64–128 | ~10–15% |
| `parent_max_tokens` | 2048 (cap) | Truncate section cực dài trước khi store |
| `embed_with_heading_prefix` | `true` | Thử tắt nếu noise |
| `strategy_id` | `heading_recursive_parent_child` | Log / versioning |

---

## 8. Pseudo-code ingest chunk

```text
function chunk_document(markdown, meta):
  sections = split_by_headings(markdown, levels=1..3)
  parents = []
  children = []
  chunk_index = 0

  for i, section in enumerate(sections):
    parent_id = f"{meta.document_id}::s{i}"
    parent_text = maybe_cap(section.text, parent_max_tokens)
    parents.append(ParentRecord(parent_id, parent_text, section.heading_path, …))

    pieces = recursive_split(section.text, max_tokens, overlap)
    # nếu section ngắn: pieces = [section.text]

    for piece in pieces:
      children.append(Chunk(
        text=piece,
        parent_id=parent_id,
        heading_path=section.heading_path,
        filename=meta.filename,
        chunk_index=chunk_index,
        …
      ))
      chunk_index += 1

  return parents, children
```

Sau đó: `save_parents(parents)` → `embed(children)` → `upsert` vào `proj_{project_id}`.

---

## 9. Pseudo-code retrieve

```text
function retrieve(query, project_id, k):
  collection = f"proj_{project_id}"
  hits = qdrant.search(collection, embed(query), limit=k)
  # hits: child payloads

  parents_by_id = load_parents(unique(hit.parent_id for hit in hits))
  docs = []
  seen_parents = set()
  for hit in hits:
    if hit.parent_id in seen_parents: continue  # hoặc giữ nhiều child score
    seen_parents.add(hit.parent_id)
    p = parents_by_id[hit.parent_id]
    docs.append({
      child_text: hit.text,
      parent_text: p.parent_text,
      parent_id: hit.parent_id,
      heading_path: hit.heading_path,
      filename: hit.filename,
      document_id: hit.document_id,
      score: hit.score,
    })
  return docs
```

---

## 10. So với kỹ thuật khác (bối cảnh học)

| Kỹ thuật | Quan hệ với chốt hiện tại |
|---|---|
| Fixed-size + overlap | Baseline — ta **không** dùng làm mặc định |
| Recursive character/token | **Có** — tầng 2 trong section |
| Markdown / heading split | **Có** — tầng 1 |
| Semantic chunking | Không MVP (cần embed để quyết định cắt) |
| `pymupdf4llm.to_chunks` | Layout PDF trực tiếp; ta chunk trên MD sau convert |
| Parent–child / small-to-big | **Có** — tầng retrieve |
| Sentence window | Biến thể expand; ta expand theo **section parent** |

---

## 11. Code dự kiến

```text
rag/ingest/chunking.py     # split_by_headings, recursive_split, chunk_document
rag/ingest/types.py        # Chunk, ParentRecord
rag/parents.py             # save / get / delete by document_id
rag/vectorstore.py         # collection per project, upsert children
rag/retriever.py           # search + expand parents + citation fields
```

Tests gợi ý: MD có/không heading; section dài có overlap; dedupe parent lúc retrieve; cap parent.

## 12. Khi đổi gì thì đụng đâu

| Đổi | Đụng |
|---|---|
| Logic cắt heading / recursive | `chunking.py` + unit tests |
| Schema parent / payload | `types.py`, parents store, vectorstore, retriever, docs này |
| Chỉ đổi cách generate cite | prompt generate + shape documents |
| Đổi sang Cách A (parent trong payload) | vectorstore + bỏ/giảm parents store — **không** phải hướng hiện tại |

---

## Tham chiếu nhanh

| Doc | Nội dung |
|---|---|
| [`ingest-pipeline.md`](./ingest-pipeline.md) | Toàn pipeline upload → convert → dedup → chunk → embed → upsert |
| [`../agent/generate-and-rag-ports.md`](../agent/generate-and-rag-ports.md) | Port retrieve/rerank/generate trong agent |
