# Nghiệm thu Tuần 3

Ngày lập: 2026-11-25 (Buổi 7). Tiêu chí lấy từ `docs/PROMPT_WEEK3.md`, mục "Tiêu chí nghiệm thu Tuần 3". Nhật ký chi tiết (lệnh, kết quả thật, phần chưa kiểm chứng) ở `docs/ENVIRONMENT_CHECK.md`, mục "Tuần 3 — Buổi 7" và các buổi trước.

**Ý nghĩa trạng thái:**
- **ĐẠT**: Claude đã chạy và có bằng chứng.
- **CHƯA ĐẠT**: đã kiểm và không đạt.
- **CHƯA KIỂM CHỨNG**: chưa có bằng chứng; không suy đoán.

## Tóm tắt

- 7 tiêu chí của Tuần 3: **5 tiêu chí ĐẠT**.
- Có **2 tiêu chí ĐẠT một phần**. Phần còn lại của chúng là CHƯA KIỂM CHỨNG, ghi rõ ở từng dòng của bảng dưới:
  - Tiêu chí 1: chất lượng trả lời thật theo trình độ.
  - Tiêu chí 7: bước `docker compose` trên bản sao sạch ở Buổi 7.
- Chưa có tiêu chí nào CHƯA ĐẠT.
- 9 mục thử trên trình duyệt: **CHƯA KIỂM CHỨNG**. Người dùng sẽ tự thử.

## Tiêu chí nghiệm thu

| # | Tiêu chí | Trạng thái | Bằng chứng |
| --- | --- | --- | --- |
| 1a | Lịch sử chat được lưu, đúng thứ tự, đúng chủ sở hữu | **ĐẠT** | `test_e2e_week3.py::test_chat_flow_register_login_send_and_read_history_in_order`; `test_chat_api.py`, `test_chat_history.py`. Chat thật qua toàn bộ API ở Buổi 3: HTTP 200, lịch sử đọc lại `[user ok, assistant ok]` |
| 1b | Người dùng không truy cập được phiên của người khác | **ĐẠT** | `test_e2e_week3.py::test_other_user_cannot_read_or_write_session`: đọc, ghi hay đoán phiên của người khác đều nhận 404 giống hệt nhau, không ghi thêm tin. Làm hỏng có chủ đích (bỏ điều kiện `user_id`) → test đỏ |
| 1c | Prompt theo đúng ngôn ngữ và trình độ của hồ sơ | **ĐẠT** | System prompt dựng từ `prompts/<language_code>/tutor.md` với `level_code` của hồ sơ. Test e2e kiểm prompt chứa A1; sau khi áp dụng placement, phiên mới mang B1 (`test_placement_flow_…`); `test_prompts.py` |
| 1d | Model thật trả lời bằng tiếng Việt, theo trình độ | **ĐẠT một phần** | Bằng tiếng Việt: ĐẠT. Smoke `text` Buổi 7 (200, `gemini-3.5-flash-lite`, 42/93 token) và chat thật Buổi 3 (3072 ms, 393/295 token) đều trả lời tiếng Việt kèm ví dụ tiếng Anh. **Điều chỉnh theo trình độ: CHƯA KIỂM CHỨNG** (chưa so A1 với B1 trên model thật; đánh giá ở Tuần 7) |
| 2 | LLM lỗi, hết giờ hoặc bị giới hạn: frontend nhận mã lỗi ổn định, không lộ chi tiết nội bộ, không treo | **ĐẠT** (phía API) | `test_e2e_week3.py::test_llm_failure_…` gồm 3 ca: timeout 504 `llm_timeout`, rate limit 429 `llm_rate_limited` + `Retry-After`, content blocked 422 `llm_content_blocked`. Không lộ thông điệp nội bộ; lượt lỗi lưu `status='error'`; lượt sau trả 200. `test_chat_api.py` phủ đủ 7 mã. Timeout cho mỗi lời gọi: `LLM_TIMEOUT_SECONDS`. Lỗi thật Buổi 7: Google trả 503 → chuẩn hóa đúng thành `llm_provider_error`. Hiển thị trên giao diện: xem mục trình duyệt |
| 3 | Placement chấm đúng đáp án đã duyệt, không lộ đáp án trước khi nộp, ra trình độ đề xuất và chủ đề yếu | **ĐẠT** | `test_e2e_week3.py::test_placement_flow_…`: không có khóa đáp án khi `start`/`get`; 12/30 → A2 (ranh giới 40%); 30/30 → B1; có review, nhóm yếu, chủ đề sai, disclaimer; nộp lại → 409; áp dụng lượt cũ → 409 `placement_superseded`; hồ sơ đổi đúng. `test_placement_scoring.py`, `test_placement_api.py`, `test_placement_lifecycle.py`. Làm hỏng có chủ đích (lộ `correct_answer`; ngưỡng A2 40 → 41) → test đỏ. Bộ câu hỏi đã được Claude rà soát (`docs/EVALUATION_REVIEW.md`), chưa có giáo viên duyệt; ngưỡng là *tạm thời* |
| 4 | Giới hạn đăng nhập sai và giới hạn chat hoạt động, có test | **ĐẠT** | `test_e2e_week3.py`: tin thứ 7 trong phút → 429 `chat_rate_limited` + `Retry-After` (không lưu, không gọi LLM); sai 5 lần → 429 `auth_rate_limited`. `test_auth_limits.py`, `test_chat_limits.py`, `test_rate_limit.py`. HTTP thật qua uvicorn ở Buổi 6: `Retry-After: 60` / `900`, được expose qua CORS |
| 5 | Toàn bộ test chạy không cần mạng và không cần API key; smoke test thật tách riêng, mặc định tắt, đã chạy ít nhất một lần có báo cáo | **ĐẠT** | `GEMINI_API_KEY="" LLM_PROVIDER=fake HTTP(S)_PROXY=http://127.0.0.1:9 pytest` → **370 passed, 1 skipped** (mục skipped là smoke, không có cảnh báo). `npm test` 13/13. Smoke `test_llm_smoke.py` chỉ chạy khi `RUN_LLM_SMOKE=1`. Đã chạy thật có báo cáo: Buổi 2 (text + structured 200), Buổi 3 (chat thật qua API), Buổi 7 (text: lời gọi 200; structured: 503 từ Google) |
| 6 | Không có secret trong mã, log hay lịch sử Git; log không chứa nội dung tin nhắn | **ĐẠT** | Buổi 7: giá trị thật của key Gemini, JWT secret, mật khẩu DB có 0 lần xuất hiện trong file sẽ commit, `frontend/dist` và 14 commit; 0 chuỗi `AIza…`; `.env` chưa từng được commit. Đã đọc 13 lời gọi `logger.*`: chỉ ghi metadata. `caplog` mức DEBUG trong test e2e: không có nội dung tin |
| 7a | README và tài liệu thiết kế đã cập nhật | **ĐẠT** | README (trạng thái, Node ≥ 22.18 cho `npm test`, chạy giao diện với fake hoặc Gemini, Kiểm thử); `ARCHITECTURE.md` (luồng chat, placement, giới hạn tần suất, frontend, điểm nối RAG); `DATABASE_DESIGN.md` (Buổi 5); `.env.example` đã đối chiếu với `Settings` |
| 7b | Bản sao sạch chạy được theo README | **ĐẠT một phần** | Buổi 7, chép file sẽ commit sang thư mục tạm: venv + `pip install`, alembic, nạp placement `--dry-run`, uvicorn `/health` 200, `npm ci`, `npm test`, `npm run build`, `pytest` 370 passed/1 skipped. **Bước `docker compose up`: CHƯA KIỂM CHỨNG ở Buổi 7** (dùng chung container đang chạy). File compose không đổi từ Tuần 2, khi đó đã chạy được trên bản sao sạch ở cổng 5433 |

## Kiểm tra bắt buộc của Buổi 7

| Kiểm tra | Kết quả |
| --- | --- |
| `pytest` (không mạng, không key) | 370 passed, 1 skipped (smoke), 0 cảnh báo |
| `npm test` / `npm run build` | 13/13 / pass |
| `alembic` trên DB test: upgrade → check → downgrade -1 → upgrade → check | Đều đạt, không lệch |
| `alembic current` / `check` trên DB chính (chỉ đọc) | `dfd85f565969 (head)`, không lệch |
| `validate_dataset.py` / `validate_evaluation.py` | 15 bài, 0 lỗi / 30 câu placement, 30 truy vấn (20 dev, 10 test) |
| Làm hỏng code có chủ đích (test e2e) | Kiểm chủ sở hữu → 1 failed; lộ đáp án → 1 failed; ngưỡng A2 → 1 failed; lưu lượt lỗi thành `ok` → 3 failed. Khôi phục, `cmp` đều khớp |

## Thử trên trình duyệt (người dùng tự thử)

Claude không quan sát được trình duyệt, nên không tự điền "đạt" cho các mục này. Hướng dẫn chi tiết có trong báo cáo Buổi 6. Chạy backend với `LLM_PROVIDER=fake` trừ khi mục ghi khác.

| # | Mục | Trạng thái | Cách thử |
| --- | --- | --- | --- |
| T1 | Chat cơ bản | **CHƯA KIỂM CHỨNG — người dùng sẽ tự thử** | Gửi tin, thấy tin hiện ngay rồi có trả lời. Tạo phiên mới; tiêu đề lấy từ tin đầu; F5 vẫn còn lịch sử |
| T2 | Enter / Shift+Enter / gõ Telex | **CHƯA KIỂM CHỨNG — người dùng sẽ tự thử** | Enter gửi đúng 1 lần, kể cả khi gõ dấu bằng Telex/VNI. Shift+Enter xuống dòng |
| T3 | Đếm ngược chat | **CHƯA KIỂM CHỨNG — người dùng sẽ tự thử** | Gửi nhanh 7 tin: hiện lỗi giới hạn và đếm ngược khoảng 60 giây. Chuyển tab rồi quay lại, số giây vẫn đúng. Hết giờ, "Thử lại" không làm tin bị trùng |
| T4 | Đếm ngược đăng nhập | **CHƯA KIỂM CHỨNG — người dùng sẽ tự thử** | Đăng nhập sai 6 lần: hiện "thử lại sau 15 phút …", nút bị khóa "Đợi …" |
| T5 | Thông báo | **CHƯA KIỂM CHỨNG — người dùng sẽ tự thử** | Trang chat luôn có 2 thông báo: không dẫn nguồn; dữ liệu gửi Google. Tin dài hơn 2000 ký tự bị báo lỗi và nội dung được giữ lại. (Ảnh chụp ở chế độ fake đã cho thấy 2 thông báo và bộ đếm, nhưng chưa thử đủ các thao tác của mục này) |
| T6 | Placement + áp dụng + hồ sơ | **CHƯA KIỂM CHỨNG — người dùng sẽ tự thử** | Bắt đầu, "Bỏ chọn", nộp khi còn câu trống (có hỏi xác nhận), xem lại đáp án, "Dùng trình độ này" → hồ sơ đổi. Làm lại: lượt cũ không còn nút áp dụng |
| T7 | Màn hình 360px | **CHƯA KIỂM CHỨNG — người dùng sẽ tự thử** | DevTools → thiết bị, rộng 360: menu chỉ còn biểu tượng, nút mở danh sách phiên hoạt động, không có thanh cuộn ngang |
| T8 | Focus bàn phím | **CHƯA KIỂM CHỨNG — người dùng sẽ tự thử** | Dùng Tab và phím mũi tên đi qua menu, ô chat, đáp án: luôn thấy viền xanh |
| T9 | Đổi phiên khi đang gửi | **CHƯA KIỂM CHỨNG — người dùng sẽ tự thử** | Trong lúc chờ trả lời, các phiên khác và "Cuộc trò chuyện mới" bị khóa, có dòng giải thích. Với fake, lượt gửi rất nhanh nên dễ thấy hơn khi dùng Gemini. Sau khi có trả lời, đổi phiên không bị lẫn tin |

## Giới hạn đã biết khi nghiệm thu

- Ngưỡng placement 40%/70% là *tạm thời*. Bộ câu hỏi do Claude soạn và rà soát, chưa có giáo viên duyệt (`docs/EVALUATION_REVIEW.md`).
- Bộ đếm giới hạn phút, IP và đồng thời nằm trong bộ nhớ của một tiến trình (`docs/ARCHITECTURE.md`, "Giới hạn đã biết").
- Chat là LLM-only, chưa có tài liệu tham khảo hay citation. RAG là Tuần 4; điểm nối đã ghi trong `docs/ARCHITECTURE.md`.
- Gói Gemini miễn phí: Google có thể dùng nội dung gửi lên; giao diện có thông báo.
