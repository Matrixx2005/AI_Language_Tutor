# Nghiệm thu Tuần 5 — Phần A (Streamlit console + bộ đánh giá v2)

Ngày lập: 2026-11-28. Nhật ký: `docs/ENVIRONMENT_CHECK.md` (mục "Tuần 5A"). Số đo: `experiments/README.md` (mục 3).

Ý nghĩa trạng thái:
- **ĐẠT**: Claude đã chạy và có bằng chứng.
- **CHƯA ĐẠT**: đã kiểm và không đạt.
- **CHƯA KIỂM CHỨNG**: chưa có bằng chứng.

| # | Tiêu chí | Trạng thái | Bằng chứng |
| --- | --- | --- | --- |
| 1 | `streamlit run` chạy được; đủ 7 trang; không có logic nghiệp vụ trùng lặp; backend tắt thì báo lỗi dễ hiểu, không sập | **ĐẠT** (thao tác trên trình duyệt **CHƯA KIỂM CHỨNG**) | Chạy headless ở cổng 8501: `/_stcore/health` → `ok`, trang chính → 200. `AppTest` với backend thật trên DB test (fake, hybrid, Qdrant và model thật): đăng ký → chat (3 nguồn, chế độ hybrid) → Hệ thống (LLM = fake, RAG = hybrid, PostgreSQL ok, Qdrant ok) → Retrieval Lab (đủ 3 cột) → Placement, Thí nghiệm, Corpus: **0 exception**. `AppTest` với backend tắt (cổng chết): trang Hệ thống hiện "Không kết nối được backend", không exception. Nghiệp vụ chỉ đi qua `api.py`; `logic.py` chỉ có hàm hiển thị và kiểm tra |
| 2 | Chế độ chia sẻ: cổng mã hoạt động; public mode chặn Gemini; test split không truy cập được từ giao diện; không lộ secret | **ĐẠT** | `test_streamlit_console.py` (9 test): cổng mã chặn trang mặc định khi chưa nhập mã (`AppTest`), mã sai báo lỗi, mã đúng thì vào; `chat_allowed(public, gemini)` = chặn; `dev_only` loại test split, giao diện không có test split. Làm hỏng có chủ đích 5 chỗ (bỏ cổng mã, cho đọc test split, bỏ escape, bật `unsafe_allow_html`, public mode không chặn Gemini): mỗi chỗ 1 failed, khôi phục xong `cmp` khớp. Quét secret: 0 lần xuất hiện |
| 3 | Bộ đánh giá v2 ≥ 100 truy vấn, mỗi bài ≥ 2, có nhóm expected=none, chia dev/test bằng băm cố định; 30 truy vấn cũ không đổi | **ĐẠT** | 109 truy vấn (78 dev / 31 test), 33/33 bài có 2–4 truy vấn, 10 truy vấn `none`; `validate_evaluation.py` kiểm v1 giữ nguyên, quy tắc băm, trùng lặp, độ phủ. `git diff` của file v1 và manifest cũ rỗng. 79 truy vấn mới **CHƯA DUYỆT BỞI NGƯỜI**; chỗ cho ≥ 30 truy vấn do người viết đang trống (`docs/EVAL_REVIEW_V2.md`) |
| 4 | Có số đo dev mới kèm khoảng tin cậy và so sánh Hybrid với Dense; không chỉnh tham số | **ĐẠT** | Dense R@3 0,92 [0,85; 0,97], MRR 0,843. Hybrid R@3 0,90 [0,82; 0,96], MRR 0,821. Hybrid − Dense: ΔR@3 −0,014 (p = 0,79), ΔMRR −0,022 (p = 0,51) → **khác biệt không có ý nghĩa**; Hybrid không hơn Dense. Nhóm none: hybrid không phân biệt được (57% truy vấn none có điểm ≥ trung vị nhóm có đáp án) |
| 5 | Gemini sau khi đổi prompt đã kiểm, có báo cáo thật | **ĐẠT** | 2 lời gọi (`RUN_RAG_SMOKE_LLM=1`). Hybrid 554 ký tự, dense 613 ký tự: 0 dấu `*`, bản dịch nằm trong ngoặc tròn (2 chỗ mỗi câu trả lời), 0 ngoặc vuông ngoài trích dẫn, 0 trích dẫn sai, đủ 5 nhãn, [1] trỏ đúng bài |
| 6 | Test mặc định không cần mạng/key; không có secret trong mã, log, Git | **ĐẠT** | `pytest` (không mạng, không key): **412 passed, 5 skipped** (đều là smoke). `npm test` 21/21, build đạt. Key, JWT secret, mật khẩu DB: 0 lần xuất hiện trong file sẽ commit, `dist` và lịch sử Git; `streamlit_app/` không ghi token ra đĩa |

## Người dùng tự thử trên trình duyệt (CHƯA KIỂM CHỨNG)

1. Chạy `streamlit run streamlit_app/app.py --server.address 127.0.0.1 --server.port 8501` và đi qua 7 trang.
2. Ở trang Chat: chọn chế độ, mở nguồn, xem dòng "trích dẫn hợp lệ / không hợp lệ".
3. Đặt `$env:STREAMLIT_ACCESS_CODE`, chạy lại: mọi trang phải hỏi mã.
4. Đặt `$env:STREAMLIT_PUBLIC_MODE="true"` khi backend đang dùng `gemini`: chat bị chặn và có cảnh báo đỏ.
5. (Tùy chọn) `cloudflared tunnel --url http://127.0.0.1:8501`, mở link trên điện thoại, nhập mã truy cập.
