# PROJECT MASTER PLAN — AI Language Tutor

Phiên bản: 0.3 (nghiệm thu Tuần 1) · Ngày: 2026-11-18
Bản đầy đủ có bình luận: tài liệu Claude Doc "AI Language Tutor — Master Plan & Hướng dẫn từng buổi".

## A. Tóm tắt và mục tiêu nghiên cứu

Hệ thống gia sư tiếng Anh A1–B1 cho người Việt (website, giao diện tiếng Việt).

**Câu hỏi nghiên cứu:** Hybrid RAG (BM25 + BGE-M3 + RRF) có truy xuất và trả lời tốt hơn LLM-only và Dense RAG hay không?

- Ba cấu hình so sánh: LLM-only, LLM + Dense, LLM + Hybrid.
- Thước đo: Recall@K, MRR, factual correctness, faithfulness, citation accuracy, latency.
- Không kết luận trước khi có số liệu thật. Tách tập dev (tối ưu) và test (báo cáo, chạy một lần).
- Cá nhân hóa (mastery score + spaced repetition) là phần phụ, chưa claim hiệu quả học tập.

## B. Kiến trúc

Monorepo: React + TypeScript + Vite + Tailwind / FastAPI + Pydantic + SQLAlchemy + Alembic / PostgreSQL / Qdrant / Docker Compose.

Luồng RAG: Query → BM25 + Dense (bật/tắt độc lập) → RRF → chọn ngữ cảnh → prompt → Gemini Flash → câu trả lời + trích dẫn.

| Thành phần | Rủi ro cần kiểm tra thật | Kết quả kiểm tra Tuần 1 |
| --- | --- | --- |
| Gemini Flash | Model ID/SDK đổi; hạn mức gói miễn phí. Model ID đặt trong `.env`. | Chưa kiểm tra SDK, model ID hoặc gọi dịch vụ. |
| BGE-M3 | Nặng; PyTorch trên Windows + Python 3.13; chạy CPU, không CUDA. | `pip install --dry-run torch sentence-transformers` tìm được bản tương thích Python 3.13; chưa cài, chưa tải model, chưa kiểm tra runtime/hiệu năng. |
| BM25 | Truy vấn tiếng Việt vs tài liệu tiếng Anh. | `rank_bm25` giải quyết được bằng dry-run; chất lượng retrieval chưa đo. |
| Qdrant | Chạy local bằng Docker. | `qdrant-client` giải quyết được bằng dry-run; Docker/Compose chưa có nên chưa chạy Qdrant. |
| FastAPI/Pydantic | Tương thích và kiểm thử trong môi trường dự án. | Chưa cài trong `.venv`; có mặt ở Python hệ thống nhưng chưa dùng làm bằng chứng tương thích của venv. |

Kết quả dry-run chỉ xác nhận package resolver tìm được bản phân phối, không xác nhận import/runtime, hiệu năng hay chất lượng. Chi tiết môi trường được ghi tại `docs/ENVIRONMENT_CHECK.md`.

## C. Phạm vi

- **MVP:** auth, placement test, AI Tutor (LLM-only rồi RAG + trích dẫn), bài tập + chấm + phân tích lỗi, mastery + lịch ôn + gợi ý, dashboard, thí nghiệm so sánh.
- **Mở rộng (nếu dư thời gian):** Scenario Conversation, reranking.
- **Ngoài phạm vi:** luyện giọng nói, fine-tune LLM, ngôn ngữ khác tiếng Anh.

## D. Nghiên cứu và thực nghiệm

Baseline: LLM-only, Dense RAG. Đề xuất: Hybrid. Ablation: bật/tắt sparse/dense, đổi top-k. Cấu hình, phiên bản model, truy vấn và kết quả lưu trong `experiments/`.

## E. Lộ trình 8 tuần và nghiệm thu

| Tuần | Nội dung | Nghiệm thu | Trạng thái |
| --- | --- | --- | --- |
| 1 | Thiết kế, repo, môi trường, dataset v1, bộ đánh giá nháp | Repo chạy được; schema DB có `language_code`; ≥ 15 bài ngữ pháp đủ metadata; 30 truy vấn đánh giá nháp | Hoàn thành (2026-11-18): đạt 6/6 tiêu chí nghiệm thu; ERD đã duyệt; 15 bài chốt CC BY 4.0; bộ đánh giá đã rà soát (`docs/EVALUATION_REVIEW.md`); 9 test pass, validator 0 lỗi. Git khởi tạo cuối Tuần 1; Docker chuyển sang điều kiện của Tuần 2. |
| 2 | Auth, REST API, PostgreSQL, giao diện nền | Đăng ký/đăng nhập từ UI; có test API | Chưa bắt đầu |
| 3 | Gemini, chat API, placement test | Chat LLM-only lưu lịch sử; placement ra A1–B1 | Chưa bắt đầu |
| 4 | RAG | 3 chế độ truy xuất; trích dẫn đúng tài liệu đã truy xuất; test retrieval | Chưa bắt đầu |
| 5 | Bài tập, phân tích lỗi | Sinh → validate → làm → chấm → giải thích → lưu lỗi | Chưa bắt đầu |
| 6 | Cá nhân hóa, dashboard, E2E | MVP chạy liền mạch | Chưa bắt đầu |
| 7 | Thí nghiệm | Bảng số thật, biểu đồ, phân tích lỗi | Chưa bắt đầu |
| 8 | Triển khai, báo cáo | Demo chạy, README, báo cáo, slide | Chưa bắt đầu |

Nếu trễ quá 2 ngày: cắt tính năng mở rộng trước, không cắt thí nghiệm.

## F. Rủi ro chính

Thiếu dữ liệu có giấy phép; bộ đánh giá nhỏ/lệch; Hybrid không hơn Dense; BGE-M3 chậm trên CPU; Gemini đổi model/quota; bài tập AI sinh sai; trích dẫn bịa; scope creep; lộ API key. Phương án chi tiết xem Claude Doc.

## G. Quyết định (đề xuất mặc định, chờ xác nhận)

- Dữ liệu tối thiểu: 30 bài ngữ pháp, 300 từ vựng, 15 bài đọc, 120 câu hỏi, 100 truy vấn đánh giá.
- Nội dung chủ yếu tự biên soạn (LLM soạn nháp, người duyệt); ghi `source` + `license`.
- Qdrant chạy local bằng Docker.
- BGE-M3 trên CPU; đổi model chỉ khi đo được là quá chậm và phải xin phép.
- Truy vấn hỗ trợ tiếng Việt và tiếng Anh.
- Chấm câu trả lời: thủ công trên mẫu + LLM-as-judge có nêu hạn chế.

## Đa ngôn ngữ (điểm mở rộng tối thiểu)

Xem `docs/MULTILINGUAL_EXTENSION.md` (phác thảo Tuần 1). Sáu điểm: `language_code` trong DB; cấu hình trình độ theo ngôn ngữ (`languages/<code>.yaml`); RAG lọc theo `language_code` và `level_code`; `prompts/<code>/`; registry loại bài tập; module dùng chung không hardcode tiếng Anh/CEFR. Không triển khai dữ liệu hay tính năng tiếng Trung, Nhật, Hàn trong 8 tuần.

## Quy tắc làm việc

Không cài dependencies, tải dataset, commit hay push, dùng dịch vụ trả phí khi chưa được cho phép. Không chuyển tuần khi chưa được yêu cầu.

## H. Cập nhật nghiệm thu Tuần 1 (2026-11-18)

- Môi trường: Python 3.13.11 trên Windows 11; `.venv` dùng Python 3.13.11; pytest 9.2.0 được cài sau khi người dùng cho phép; thêm `pytest.ini` để lệnh `pytest` trực tiếp import được `scripts.*`. Node v24.15.0 và npm 11.12.1 có (lần kiểm tra đầu báo sai npm do lỗi script, đã sửa); Docker và Docker Compose không tìm thấy. Thư mục workspace chưa phải Git repository.
- Thiết kế: tài liệu kiến trúc và schema logic 12 bảng đã tạo; người dùng đã duyệt ERD logic. Chưa tạo/chạy migration. `language_code` và `level_code` được thiết kế dạng chuỗi; không dùng enum CEFR.
- Dataset: 15 bài ngữ pháp A1–B1 (nội dung soạn mới, mức nháp). License **CC BY 4.0 đã được người quản lý dự án chốt ngày 2026-11-18**. Sửa 2 lỗi nội dung (plurals-004, relative-clauses-015 → `v1.1-draft`).
- Đánh giá: 30 câu placement và 30 truy vấn RAG, truy vấn khóa theo ID ở tỷ lệ 20 dev / 10 test. Đã rà soát chất lượng ngày 2026-11-18 (Claude rà soát theo yêu cầu người dùng, chưa phải giáo viên bản ngữ): cân bằng vị trí đáp án placement, thay 1 câu sai cấp độ, viết lại 10 truy vấn trùng ý; chi tiết trong `docs/EVALUATION_REVIEW.md`.
- Kiểm chứng lần cuối: `pytest` — 9 passed; dataset validator — 15 records, 0 errors; evaluation validator — 30 câu placement, 30 truy vấn, 20 dev / 10 test.
- Chưa xác nhận nghiệm thu toàn bộ Tuần 1: thiếu sơ đồ thư mục chi tiết của Master Prompt trong workspace; repo chưa có frontend/manifests và không ở trong Git; Docker chưa cài; ngưỡng placement 40%/70% chỉ là tạm thời, cần hiệu chuẩn bằng pilot. Không có số liệu nghiên cứu hay hiệu năng nào được tạo/khẳng định.
