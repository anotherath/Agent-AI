# Ý tưởng sản phẩm

## Project

Không gian làm việc riêng của user. Mỗi project có:

- Mô tả project
- Persona
- File `.md` ghi nhớ riêng của project
- Context RAG từ tài liệu đã ingest/embed (file + metadata lưu trên Cloudflare R2, vector lưu trên Qdrant)

## Session

Một cuộc hội thoại. Có thể:

- Gắn với một project, hoặc không gắn project
- **Khi một session đã được gắn với một project thì gắn mãi mãi với project đó**, không thể chuyển sang project khác hoặc bỏ gắn
- Có context riêng của session
- Chứa file được upload trong session
- Có một **luồng chính**; từ luồng chính có thể tạo nhiều **subsession** (nhánh fork)
- Có thể **pin** session (main hoặc sub, tối đa 3/user chung) để nổi trên danh sách

## Subsession

- Chỉ fork được từ session chính, không fork tiếp từ subsession
- Khi fork, subsession kế thừa toàn bộ context lịch sử từ đầu session chính đến điểm fork (không lấy phần sau điểm fork trên nhánh chính)
- Sau điểm fork, subsession chat độc lập với nhánh chính
- Subsession chỉ thuộc về một session chính, không có Take Note riêng
- Pin / auto-title giống main (title fork luôn null → auto ở tin đầu)

## Take Note

- Gắn với session chính
- Là ghi chú riêng của user, AI không đọc được và không đưa vào context
- Không liên quan đến subsession

## File upload

- **Session có project:**
  Sau khi upload/convert, file mặc định chỉ là context của session.
  Hiện lựa chọn “Embed vào Project” → chỉ khi user xác nhận thì mới embed vào RAG của Project (Qdrant).

- **Session không có project:**
  Không hiện lựa chọn embed. File chỉ trở thành context của session.

## Sửa / hỏi lại theo đoạn chat

- Sửa tin nhắn mới nhất trên luồng chính → tiếp tục trên session chính
- Sửa tin nhắn cũ trên luồng chính → fork ra subsession từ điểm đó
- Bôi đen một đoạn chat → chọn hỏi tiếp ở session chính hoặc ở subsession
