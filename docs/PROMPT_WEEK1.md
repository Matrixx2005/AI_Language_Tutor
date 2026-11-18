# PROMPT TUẦN 1 — AI LANGUAGE TUTOR



---

Hãy thực hiện **Tuần 1: Phân tích và chuẩn bị dữ liệu**. Chỉ làm Tuần 1, không tự chuyển sang Tuần 2.

## Bước 1 — Kiểm tra hiện trạng (chỉ đọc)
- Đọc `README.md`, `docs/PROJECT_MASTER_PLAN.md`, `docs/ENVIRONMENT_CHECK.md` (nếu có).
- Liệt kê cấu trúc thư mục, kiểm tra Git status, file đã có (`scripts/check_env.py`, `backend/tests/test_smoke.py`, `.env.example`, `.gitignore`).
- Không viết lại phần đã hoàn thiện.

## Bước 2 — Lập kế hoạch ngắn
Nêu mục tiêu tuần, danh sách việc, file sẽ tạo/sửa, thư viện cần dùng, rủi ro và các việc cần tôi cho phép. **Chờ tôi xác nhận** rồi mới triển khai.

## Bước 3 — Triển khai theo từng buổi (dừng sau mỗi buổi để tôi duyệt)

**Buổi 1 — Môi trường.** Đọc kết quả `docs/ENVIRONMENT_CHECK.md`, lập bảng "đã có / thiếu". Nếu thiếu Python 3.13, Docker hoặc Node: báo tôi và đề xuất cách xử lý, không tự cài.

**Buổi 2 — Repo và tương thích.**
- Hoàn thiện khung repo theo sơ đồ trong Master Prompt; chỉ tạo thư mục có nội dung.
- Xin phép trước khi cài `pytest`, FastAPI, Pydantic; chạy `pytest` để pass test mẫu.
- Kiểm tra khả năng cài PyTorch, sentence-transformers hoặc FlagEmbedding, qdrant-client, rank_bm25 trên Python 3.13 bằng `pip install --dry-run` (cảnh báo tôi nếu lệnh có thể tải file lớn). Không tải BGE-M3.
- Ghi kết quả thật, kể cả phần không tương thích, vào `docs/ENVIRONMENT_CHECK.md`.

**Buổi 3 — Kiến trúc và database.**
- Viết `docs/ARCHITECTURE.md` (thành phần, luồng RAG, quyết định kỹ thuật kèm lý do).
- Thiết kế `docs/DATABASE_DESIGN.md` với sơ đồ ER cho: users, learner_profiles, documents, lessons, questions, placement_results, attempts, error_logs, mastery, review_schedule, chat_sessions, chat_messages.
- Các bảng dữ liệu học có `language_code` (mặc định `en`) và `level_code` dạng chuỗi, không dùng enum CEFR.
- Tạo `languages/en.yaml` (A1, A2, B1, tên hiển thị, ngưỡng placement) và `prompts/en/` có README ngắn.
- Chưa chạy migration.

**Buổi 4 — Dataset v1.**
- Chốt schema tài liệu: `document_id, title, level, topic, language, content, source, license, version` (thêm `language_code` nếu tách khỏi `language`).
- Viết script validate schema và kiểm tra trùng lặp, có test.
- Cùng tôi soạn ít nhất 15 bài ngữ pháp A1–B1: bạn soạn nháp, tôi duyệt; ghi `source` và `license` cho từng bài. Không sao chép sách có bản quyền, không tải dataset lớn.

**Buổi 5 — Bộ đánh giá ban đầu.**
- Soạn khoảng 30 câu placement (ngữ pháp + từ vựng) có đáp án và nhãn chủ đề.
- Soạn 30 truy vấn đánh giá RAG nháp, mỗi truy vấn gán `document_id` liên quan, loại truy vấn (vi/en, thuật ngữ/ngữ nghĩa) và nhãn `dev` hoặc `test`. Khóa tỷ lệ dev/test ngay từ đầu.
- Lưu trong `data/evaluation/` và viết script validate.

**Buổi 6 — Nghiệm thu.**
- Chạy lại toàn bộ test và script validate.
- Cập nhật `docs/PROJECT_MASTER_PLAN.md`; phác thảo `docs/MULTILINGUAL_EXTENSION.md`.
- Kiểm tra không có logic riêng tiếng Anh trong module dùng chung (khi đã có code).

## Quy tắc bắt buộc
- Python 3.13 trong `.venv`; không cài thêm bản Python khác.
- Xin phép trước khi: cài dependencies, tải model/dataset, xóa hoặc ghi đè file, chạy migration, dùng dịch vụ trả phí, commit, push.
- Không tạo số liệu giả rồi trình bày như dữ liệu thật. Không hardcode credentials. Không đưa API key vào log hoặc Git.
- Không nói đã hoàn thành nếu chưa chạy kiểm chứng.

## Tiêu chí nghiệm thu Tuần 1
- `pytest` pass; script validate dataset báo 0 lỗi.
- Schema DB có `language_code`; sơ đồ ER đã được tôi duyệt.
- Ít nhất 15 bài ngữ pháp đủ metadata, `source` và `license`.
- 30 câu placement và 30 truy vấn đánh giá nháp đã gán nhãn, tỷ lệ dev/test đã khóa.
- `docs/ENVIRONMENT_CHECK.md` ghi kết quả thật.

## Báo cáo cuối mỗi buổi
1. Việc đã hoàn thành. 2. File đã tạo hoặc sửa. 3. Lệnh chạy. 4. Kết quả kiểm thử thực tế. 5. Phần chưa hoàn thiện. 6. Quyết định cần tôi đưa ra. 7. Việc tiếp theo.
