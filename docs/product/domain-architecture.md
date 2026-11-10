# Kiến trúc domain: Project / Chat / File

Spec sản phẩm: [`idea.md`](./idea.md).  
Tài liệu này chốt **bảng Postgres** và **API HTTP** cho domain chat/project/file.

Auth đăng nhập (Google OAuth + cookie) đã có sẵn — xem mục [Bảng auth hiện có](#bang-auth-hien-co).  
Runtime LangGraph: `docs/architecture/agent/`.

---

## 1. Phân tầng

```text
FE (cookie session)
  → app/ FastAPI  /api/v1/...
       → Postgres (Supabase): quan hệ + metadata
       → Cloudflare R2: bytes file
       → (phase sau) rag/ → Qdrant: vector project
```

| Thành phần | Vai trò |
|---|---|
| Postgres | Source of truth: user, project, chat, message, note, file metadata |
| R2 | Object storage file gốc / artifact convert |
| Qdrant | Vector RAG theo project — **phase sau** |
| `agent/` | Sinh câu trả lời từ context đã assemble — không sở hữu schema chat |

**Quy ước tên:** bảng auth cookie tên `sessions`. Bảng hội thoại tên **`chat_sessions`**. Không gộp.

---

## 2. Bảng auth hiện có

Đã migrate / đang dùng cho đăng nhập. Domain chat **không** đụng schema này ngoài `users.id`.

| Bảng | Vai trò |
|---|---|
| `users` | Account app |
| `auth_identities` | Link Google `sub` → user |
| `sessions` | Session đăng nhập (cookie → `token_hash`) |
| `oauth_transactions` | State + PKCE one-time khi login Google |

---

## 3. Bảng domain (mới)

### 3.1 Quan hệ tổng quan

```text
users
  ├── projects
  │     └── project_embeddings   (phase sau)
  │
  └── chat_sessions (is_main = true)
        ├── project_id?          (optional; immutable sau khi set)
        ├── messages
        ├── take_notes
        ├── files                (R2; project_id NULL cho đến khi embed)
        └── chat_sessions (is_main = false)  ← subsession
              ├── parent_session_id
              ├── forked_from_message_id
              └── messages
```

### 3.2 `projects`

| Cột | Kiểu | Constraint / ghi chú |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | NOT NULL, FK → `users(id)` ON DELETE CASCADE |
| `name` | TEXT | NOT NULL |
| `description` | TEXT | nullable |
| `persona` | TEXT | nullable |
| `icon` | TEXT | NOT NULL, default `folder` — id icon UI (`folder`, `code`, `bot`, …) |
| `memory_md` | TEXT | nullable — ghi nhớ `.md` của project (AI có thể dùng; **khác** take note; phase sau) |
| `created_at` | TIMESTAMPTZ | NOT NULL, default now() |
| `updated_at` | TIMESTAMPTZ | NOT NULL, default now() |

Index: `(user_id)`.

### 3.3 `chat_sessions`

| Cột | Kiểu | Constraint / ghi chú |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | NOT NULL, FK → `users(id)` ON DELETE CASCADE |
| `project_id` | UUID | nullable, FK → `projects(id)` ON DELETE **RESTRICT** |
| `title` | TEXT | nullable |
| `is_main` | BOOLEAN | NOT NULL, default true |
| `is_pinned` | BOOLEAN | NOT NULL, default false — chỉ dùng cho session main |
| `pinned_at` | TIMESTAMPTZ | nullable — lúc pin; dùng sort trong nhóm pinned |
| `last_message_at` | TIMESTAMPTZ | nullable — lần nhắn/sửa tin cuối; **main** còn được bump khi sub có tin |
| `parent_session_id` | UUID | nullable, FK → `chat_sessions(id)` ON DELETE CASCADE |
| `forked_from_message_id` | UUID | nullable, FK → `messages(id)` ON DELETE RESTRICT |
| `created_at` | TIMESTAMPTZ | NOT NULL, default now() |
| `updated_at` | TIMESTAMPTZ | NOT NULL, default now() — metadata (pin/title/…) + message activity |

**CHECK:**

- Main: `is_main = true` ⇒ `parent_session_id IS NULL` AND `forked_from_message_id IS NULL`
- Sub: `is_main = false` ⇒ `parent_session_id IS NOT NULL` AND `forked_from_message_id IS NOT NULL`

**Rule enforce (app + trigger):**

1. Subsession chỉ được tạo từ session `is_main = true` (fork 1 cấp).
2. Subsession kế thừa `user_id` (và `project_id` nếu có) từ parent; không tự đổi.
3. Khi `project_id` đã khác NULL: **cấm** UPDATE thành NULL hoặc sang project khác.
4. Subsession không có take note.
5. Pin chỉ trên session main; mỗi user tối đa **3** session pinned.

Index: `(user_id, updated_at DESC)`, `(user_id, is_pinned, pinned_at)`, `(project_id)`, `(parent_session_id)`.

### 3.4 `messages`

| Cột | Kiểu | Constraint / ghi chú |
|---|---|---|
| `id` | UUID | PK |
| `session_id` | UUID | NOT NULL, FK → `chat_sessions(id)` ON DELETE CASCADE |
| `role` | TEXT | NOT NULL — `user` \| `assistant` \| `system` |
| `content` | TEXT | NOT NULL |
| `metadata` | JSONB | nullable |
| `created_at` | TIMESTAMPTZ | NOT NULL, default now() |

Index: `(session_id, created_at)`.

**Assemble context (không copy message khi fork):**

| Chat đang mở | Context gửi agent |
|---|---|
| Main | `messages` của main, sort `created_at` |
| Subsession | `messages` của **parent** với `created_at` ≤ message `forked_from_message_id`, **cộng** `messages` của subsession |

### 3.5 `take_notes`

| Cột | Kiểu | Constraint / ghi chú |
|---|---|---|
| `id` | UUID | PK |
| `session_id` | UUID | NOT NULL, FK → `chat_sessions(id)` ON DELETE CASCADE |
| `title` | TEXT | nullable |
| `content` | TEXT | NOT NULL |
| `created_at` | TIMESTAMPTZ | NOT NULL, default now() |
| `updated_at` | TIMESTAMPTZ | NOT NULL, default now() |

**Rule:** chỉ gắn `chat_sessions.is_main = true`. Enforce bằng app/trigger.  
**AI không đọc** — không đưa vào prompt / RAG / memory agent.

### 3.6 `files`

| Cột | Kiểu | Constraint / ghi chú |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | NOT NULL, FK → `users(id)` ON DELETE CASCADE |
| `session_id` | UUID | nullable, FK → `chat_sessions(id)` ON DELETE CASCADE |
| `project_id` | UUID | nullable, FK → `projects(id)` ON DELETE RESTRICT — **chỉ set khi embed** |
| `original_name` | TEXT | NOT NULL |
| `mime_type` | TEXT | nullable |
| `size_bytes` | BIGINT | nullable |
| `r2_key` | TEXT | NOT NULL |
| `converted_r2_key` | TEXT | nullable — artifact `.md`/text nếu convert |
| `status` | TEXT | NOT NULL — `uploaded` \| `converted` \| `embedded` |
| `created_at` | TIMESTAMPTZ | NOT NULL, default now() |
| `updated_at` | TIMESTAMPTZ | NOT NULL, default now() |

CHECK: `session_id IS NOT NULL OR project_id IS NOT NULL`.

**Phase hiện tại:** upload → R2 → `status=uploaded` (+ optional convert → `converted`). `project_id` luôn NULL.  
**Phase sau:** user xác nhận embed → set `project_id`, ghi `project_embeddings`, `status=embedded`.

### 3.7 `project_embeddings` (schema mở — implement sau)

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | UUID | PK |
| `project_id` | UUID | FK → `projects(id)` ON DELETE CASCADE |
| `file_id` | UUID | FK → `files(id)` ON DELETE CASCADE |
| `qdrant_point_ids` | TEXT[] | nullable |
| `embedded_at` | TIMESTAMPTZ | default now() |

UNIQUE `(project_id, file_id)`.

---

## 4. API HTTP

Base: `/api/v1`.  
Tất cả endpoint dưới đây (trừ auth đã có) yêu cầu **cookie session đăng nhập**, trừ khi ghi chú khác.

Auth đã có (không đổi trong doc này):

| Method | Path | Mô tả |
|---|---|---|
| GET | `/auth/google/login` | Bắt đầu Google OAuth |
| GET | `/auth/google/callback` | Callback OAuth → set cookie |
| GET | `/auth/me` | User hiện tại |
| POST | `/auth/logout` | Revoke session + xóa cookie |
| GET | `/health` | Health + ping DB |

### 4.1 Projects

| Method | Path | Mô tả |
|---|---|---|
| GET | `/projects` | List project của user |
| POST | `/projects` | Tạo project (`name`, `description?`, `persona?`, `icon?` default `folder`, `memory_md?`) |
| GET | `/projects/{project_id}` | Chi tiết project |
| PATCH | `/projects/{project_id}` | Sửa name / description / persona / icon / memory_md |
| DELETE | `/projects/{project_id}` | Xóa project (RESTRICT nếu còn chat gắn project) |

### 4.2 Chat sessions

| Method | Path | Mô tả |
|---|---|---|
| GET | `/chat/sessions` | List session chính (phân trang). Query: `project_id?`, `limit` (default 20, max 100), `offset` (default 0). Response: `{items, total, limit, offset, has_more}` — sort pinned → `updated_at`. Mỗi item có `run_status`, `active_run_id`, `last_read_at`, `last_message_at`, `has_unread` |
| POST | `/chat/sessions` | Tạo session chính (`title?`, `project_id?` — set thì gắn mãi) |
| GET | `/chat/sessions/{session_id}` | Chi tiết + metadata (main/sub, project, fork point, run/read state) |
| POST | `/chat/sessions/{session_id}/read` | Đánh dấu đã đọc (`last_read_at=now` → `has_unread=false`). Không đổi `updated_at` |
| PATCH | `/chat/sessions/{session_id}` | Đổi `title` only; **không** cho đổi `project_id` |
| POST | `/chat/sessions/{session_id}/pin` | Pin session main (tối đa 3/user; 409 nếu đủ slot) |
| DELETE | `/chat/sessions/{session_id}/pin` | Unpin session |
| DELETE | `/chat/sessions/{session_id}` | Xóa session (main xóa cascade sub + messages + notes + files session) |
| GET | `/chat/sessions/{session_id}/subsessions` | List subsession của một main |
| POST | `/chat/sessions/{session_id}/fork` | Fork subsession từ main. Body: `forked_from_message_id`, `title?`. Chỉ khi `session_id` là main |

### 4.3 Messages & chat

| Method | Path | Mô tả |
|---|---|---|
| GET | `/chat/sessions/{session_id}/messages` | List message của đúng session đó (kèm `metadata.steps` nếu đã lưu) |
| GET | `/chat/sessions/{session_id}/context` | Context đã assemble (main prefix + sub) — dùng debug/FE |
| POST | `/chat/sessions/{session_id}/messages` | **Stream** (SSE). Body: `content`, optional `file_ids[]`. Xem [§4.6](#46-streaming-sse--cac-buoc-suy-luan--thuc-thi). **409** nếu session đang `run_status=running` |
| POST | `/chat/sessions/{session_id}/messages/{message_id}/edit` | Sửa trên **main** rồi **stream** tiếp (cùng protocol SSE). Message mới nhất → tiếp tục main; message cũ → fork subsession rồi stream trên sub. Body: `content`. **409** nếu đang running |
| POST | `/chat/sessions/{session_id}/ask-from-selection` | Bôi đen đoạn → hỏi tiếp (**SSE**). Body: `message_id`, `selected_text`, `target`: `main` \| `subsession`. **409** nếu đang running |
| GET | `/chat/sessions/{session_id}/runs/{run_id}/stream` | **Reconnect** SSE tới run đang chạy / vừa xong (replay history + live). Dùng khi FE mất kết nối nhưng `active_run_id` còn |

Chat với agent **luôn streaming**. Agent chạy **nền** (không hủy khi SSE disconnect). Không có biến thể “chờ full response rồi mới trả JSON” cho các endpoint trên (trừ lỗi validation trước khi mở stream).

### 4.4 Take notes (chỉ session chính)

| Method | Path | Mô tả |
|---|---|---|
| GET | `/chat/sessions/{session_id}/notes` | List note (403/400 nếu không phải main) |
| POST | `/chat/sessions/{session_id}/notes` | Tạo note |
| GET | `/chat/sessions/{session_id}/notes/{note_id}` | Chi tiết |
| PATCH | `/chat/sessions/{session_id}/notes/{note_id}` | Sửa title/content |
| DELETE | `/chat/sessions/{session_id}/notes/{note_id}` | Xóa note |

### 4.5 Files (phase hiện tại: R2)

| Method | Path | Mô tả | Phase |
|---|---|---|---|
| POST | `/chat/sessions/{session_id}/files` | Upload multipart → R2 → row `files` (`status=uploaded`) | **Now** |
| GET | `/chat/sessions/{session_id}/files` | List file của session | **Now** |
| GET | `/files/{file_id}` | Metadata file | **Now** |
| POST | `/files/{file_id}/convert` | Convert → `.md`/text, cập nhật `converted_r2_key`, `status=converted` (dùng làm context session) | **Now** |
| DELETE | `/files/{file_id}` | Xóa metadata + object R2 (chặn nếu đã embedded — phase sau) | **Now** |
| POST | `/files/{file_id}/embed` | Embed vào project của session (chỉ khi session có `project_id`) | **Later** |
| GET | `/projects/{project_id}/files` | List file đã embed vào project | **Later** |

UI rule (FE): chỉ hiện “Embed vào Project” khi session có `project_id`. API `embed` cũng phải reject nếu session không có project.

### 4.6 Streaming (SSE) — các bước suy luận / thực thi

Transport: **Server-Sent Events** (`Content-Type: text/event-stream`), cookie auth như các API khác (`credentials` trên FE).

Mỗi lần user gửi chat (messages / edit / ask-from-selection):

1. Server lưu **user message** (và tạo subsession nếu fork); đánh dấu `last_read_at` (user đang ở chat).
2. Nếu session đang `running` → **409**. Ngược lại tạo `run_id`, set `run_status=running`, `active_run_id`.
3. Chạy agent **background task** (sống độc lập với HTTP). Mở SSE gắn vào run (replay + live).
4. Client disconnect **không** hủy agent — FE có thể `GET .../runs/{run_id}/stream` để nối lại, hoặc poll session/`has_unread`.
5. Kết thúc: lưu **assistant message** + `metadata.steps` (và `metadata.run_id`), `run_status=completed|error`, `active_run_id=null`, event `done`.

`has_unread`: có assistant message `created_at > last_read_at` (hoặc `last_read_at` null). FE gọi `POST .../read` khi mở/xem xong session.

#### Event SSE (contract FE)

Mỗi event: `event: <type>` + `data: <json>`.

| `event` | Khi nào | `data` (ý) |
|---|---|---|
| `run_started` | Bắt đầu turn | `run_id`, `session_id`, `user_message_id` |
| `session_updated` | Auto-title (hoặc đổi metadata session) | `session_id`, `title` |
| `step_started` | Bắt đầu một bước graph/tool | `step_id`, `kind`, `name`, `title?` |
| `step_delta` | Cập nhật giữa chừng (log ngắn, tool progress) | `step_id`, `text?`, `payload?` |
| `step_finished` | Kết thúc bước | `step_id`, `status`: `ok` \| `error`, `summary?`, `payload?` |
| `message_delta` | Token câu trả lời cuối (node `generate`, stream từng phần) | `delta` |
| `message_completed` | Đã chốt nội dung assistant | `assistant_message_id`, `content` |
| `error` | Lỗi không hồi phục được trong turn | `code`, `detail` |
| `done` | Đóng stream | `run_id`, `status`: `ok` \| `error` |

`kind` gợi ý map từ graph hiện tại:

| `kind` | Ví dụ `name` | Ý nghĩa FE |
|---|---|---|
| `guard` | `input_guard`, `output_guard` | Kiểm tra an toàn |
| `route` | `orchestrator` | Phân loại / chọn nhánh (Jev/LLM) |
| `retrieve` | `retrieve`, `rerank` | Lấy / xếp tài liệu RAG |
| `tool` | tên tool (`tavily_search`, …) | Gọi tool |
| `plan` | `multi_plan`, `execute_plan`, `gather_review` | Lập / chạy / review plan |
| `generate` | `generate` | Sinh câu trả lời |

FE hiển thị timeline bước (thinking / tool / retrieve…) realtime; phần chữ trả lời bind theo `message_delta`.

#### Lưu DB

- `messages.metadata.steps`: mảng các bước đã `step_finished` (đủ để render lại timeline khi reload history).
- `messages.metadata.run_id`: correlator với stream.
- Không bắt buộc bảng `run_events` riêng ở phase 1; nếu cần audit/replay chi tiết có thể thêm sau.

#### Lỗi giữa stream

- Validation / auth fail **trước** stream → HTTP 4xx JSON như API thường.
- Đã mở SSE rồi lỗi → event `error` rồi `done` với `status=error`; user message có thể giữ, assistant message có thể không tạo hoặc lưu kèm lỗi trong metadata.

---

## 5. Ownership & bảo mật API

- Mọi resource chỉ truy cập được nếu `user_id` = user đăng nhập (hoặc thuộc session/project của user đó).
- Subsession: thao tác note → reject.
- Đổi `project_id` trên `chat_sessions` → reject.
- Fork từ subsession → reject.
- Cookie: `HttpOnly`; CORS chỉ origin trong `CORS_ORIGINS`, `credentials` bật.

---

## 6. Phase triển khai

| Thứ tự | Việc |
|---|---|
| 1 | Migrate bảng domain (`projects`, `chat_sessions`, `messages`, `take_notes`, `files`; có thể tạo sẵn `project_embeddings` trống) |
| 2 | API projects + chat sessions + messages (chưa agent cũng được stub) |
| 3 | Fork / edit / ask-from-selection |
| 4 | Take notes |
| 5 | Upload file → R2 + convert context session |
| 6 | Nối chat với LangGraph qua **SSE**: `step_*` + `message_delta` + persist `metadata.steps` |
| 7 | (Sau) Embed project → Qdrant + API embed |

---

## 7. Nguyên tắc không đàm phán

1. Auth `sessions` ≠ chat `chat_sessions`.
2. Project gắn vào chat session là **immutable**.
3. Fork **một cấp**; context sub = history main đến điểm fork + messages nhánh.
4. Take note **private**, không vào AI context.
5. File: **R2 trước**; embed project **mở schema + API later**, không block upload.
6. Chat agent **streaming (SSE)**; FE nhận cả **bước suy luận/thực thi** và **nội dung trả lời**.
