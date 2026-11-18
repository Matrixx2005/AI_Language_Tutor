# PROMPT TUẦN 2 — AI LANGUAGE TUTOR

Dán khối dưới đây vào Claude Code (thư mục `F:\AI_Language_Tutor`). Tuân thủ Master Prompt và `docs/PROJECT_MASTER_PLAN.md`.

---

Hãy thực hiện **Tuần 2: Frontend, Backend và Database**. Chỉ làm Tuần 2, không tự chuyển sang Tuần 3.

## Bước 0 — Điều kiện tiên quyết (kiểm tra trước, chưa đạt thì dừng và báo tôi)
- Tuần 1 đã nghiệm thu: `pytest` pass, `validate_dataset.py` và `validate_evaluation.py` báo 0 lỗi.
- `docs/DATABASE_DESIGN.md` (ERD) đã được tôi duyệt. Hỏi tôi xác nhận nếu chưa rõ.
- Thư mục đã là Git repository chưa. Nếu chưa, đề xuất `git init` và chờ tôi cho phép. Không commit, không push khi chưa được phép.
- Docker và Docker Compose đã có chưa (`docs/ENVIRONMENT_CHECK.md` ghi lần gần nhất là chưa). Nếu chưa có: dừng phần PostgreSQL, nêu phương án (cài Docker Desktop, hoặc PostgreSQL cài trực tiếp) kèm ảnh hưởng, chờ tôi chọn. Không tự đổi sang SQLite.

## Bước 1 — Kiểm tra hiện trạng (chỉ đọc)
Đọc README, tài liệu thiết kế, cấu trúc thư mục, test hiện có, `.env.example`. Không viết lại phần đã hoàn thiện.

## Bước 2 — Lập kế hoạch ngắn
Nêu mục tiêu, danh sách việc, file sẽ tạo/sửa, thư viện sẽ dùng (kèm lý do chọn và phiên bản tương thích Python 3.13), rủi ro, và các việc cần tôi cho phép. **Chờ tôi xác nhận** rồi mới triển khai.

## Bước 3 — Triển khai theo từng buổi (dừng sau mỗi buổi để tôi duyệt)

**Buổi 1 — Hạ tầng.**
- `docker-compose.yml` chỉ với PostgreSQL (chưa thêm Qdrant); dữ liệu qua volume, thông tin kết nối đọc từ `.env`, không hardcode mật khẩu.
- Khung backend: `backend/app/` gồm `core/` (config đọc `.env`), `db/` (engine, session), `api/` (router), endpoint `/health`.
- Ghim phiên bản dependencies vào `backend/requirements.txt`. Xin phép trước khi cài.

**Buổi 2 — Database và migration.**
- Models SQLAlchemy chỉ cho `users` và `learner_profiles` theo ERD đã duyệt. Hồ sơ có `language_code` (mặc định `en`) và `level_code` dạng chuỗi, mục tiêu học tập.
- Alembic: tạo migration đầu tiên. Xin phép trước khi chạy migration lên DB.

**Buổi 3 — Xác thực và hồ sơ (backend).**
- Đăng ký (kiểm tra email hợp lệ, trùng email), đăng nhập (JWT), băm mật khẩu bằng thuật toán chuẩn; chọn thư viện tương thích Python 3.13 và giải thích lý do.
- JWT secret và thời hạn token đọc từ `.env`. Không ghi mật khẩu hay token vào log.
- API xem/sửa hồ sơ (mục tiêu học tập, trình độ hiện tại), route bảo vệ bằng token. Schema Pydantic cho request/response, xử lý lỗi nhất quán.
- Test pytest: đăng ký trùng email, sai mật khẩu, token thiếu/hết hạn/sai, sửa hồ sơ của chính mình. Dùng DB test riêng, không đụng dữ liệu thật.

**Buổi 4 — Frontend nền.**
- Vite + React + TypeScript + Tailwind + React Router trong `frontend/`. Giao diện tiếng Việt.
- Trang đăng ký, đăng nhập, hồ sơ; bố cục chung có thanh điều hướng, trạng thái tải và thông báo lỗi.
- Gọi API qua một lớp client duy nhất, đính token, xử lý 401 (về trang đăng nhập). Địa chỉ API đặt trong biến môi trường Vite. Cấu hình CORS ở backend chỉ cho origin dev.
- Xin phép trước khi chạy `npm install`.

**Buổi 5 — Kết nối và kiểm thử toàn tuyến.**
- Chạy thử luồng: đăng ký → đăng nhập → xem và sửa hồ sơ → đăng xuất, từ giao diện.
- Chạy toàn bộ pytest backend; build frontend (`npm run build`) không lỗi.
- Cập nhật README: cách chạy DB, backend, frontend; cập nhật `.env.example` (không chứa giá trị thật).

## Quy tắc bắt buộc
- Python 3.13 trong `.venv`.
- Xin phép trước khi: cài dependencies, cài Docker, chạy migration, xóa hoặc ghi đè file, dùng dịch vụ trả phí, commit, push.
- Không làm tính năng của tuần sau (chat, placement, RAG, bài tập, dashboard). Không thêm module chưa cần.
- Module dùng chung không hardcode tiếng Anh hay CEFR; trình độ lấy từ `languages/<code>.yaml`.
- Không hardcode credentials. Không đưa API key hay secret vào log hoặc Git.
- Không nói đã hoàn thành nếu chưa kiểm chứng; không tạo số liệu giả.

## Tiêu chí nghiệm thu Tuần 2
- Đăng ký, đăng nhập, xem/sửa hồ sơ, đăng xuất chạy được từ giao diện.
- Dữ liệu người dùng lưu trong PostgreSQL; migration chạy sạch từ DB trống.
- Test API pass (kể cả các trường hợp lỗi); frontend build không lỗi.
- Không có secret trong mã nguồn; `.env` không bị Git theo dõi.
- README đủ để người khác chạy lại từ đầu.

## Báo cáo cuối mỗi buổi
1. Việc đã hoàn thành. 2. File đã tạo hoặc sửa. 3. Lệnh chạy. 4. Kết quả kiểm thử thực tế. 5. Phần chưa hoàn thiện. 6. Quyết định cần tôi đưa ra. 7. Việc tiếp theo.
