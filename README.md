# AI Language Tutor

Hệ thống hỗ trợ học tiếng Anh A1–B1 cho người Việt, dùng Retrieval-Augmented Generation (BM25 + BGE-M3 + RRF), Gemini Flash và cá nhân hóa học tập. Đồ án tốt nghiệp Khoa học máy tính.

**Trạng thái:** Tuần 3 (đang làm) — đã có đăng ký, đăng nhập, hồ sơ học tập (Tuần 2) và lớp LLM với nhà cung cấp Gemini; chat và placement chưa có. Kế hoạch: [`docs/PROJECT_MASTER_PLAN.md`](docs/PROJECT_MASTER_PLAN.md).

Hướng dẫn dưới đây viết cho **Windows + PowerShell**, chạy từ thư mục gốc dự án trừ khi ghi khác. Làm lần lượt từ bước 1 đến bước 7.

## Yêu cầu

| Công cụ | Phiên bản đã kiểm chứng | Kiểm tra |
| --- | --- | --- |
| Python | **3.13** (3.13.11) | `py -0p` |
| Node.js + npm | Node 24 (v24.15.0), npm 11 | `node --version` |
| Docker Desktop (WSL 2) | Docker 29.9, Compose v5.7 | `docker compose version` |
| Git | 2.x | `git --version` |

Docker Desktop cần WSL 2: chạy `wsl --install` trong PowerShell (Run as Administrator), khởi động lại máy, rồi cài Docker Desktop.

## 1. Môi trường Python

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements-dev.txt
```

`requirements.txt` là gói khi chạy app; `requirements-dev.txt` thêm gói kiểm thử. Mọi phiên bản đều được ghim chính xác.

## 2. Biến môi trường (`.env`)

```powershell
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(24))"   # → dán vào POSTGRES_PASSWORD
python -c "import secrets; print(secrets.token_urlsafe(64))"   # → dán vào JWT_SECRET
```

Mở `.env`, điền hai giá trị trên. `.env` đã nằm trong `.gitignore` — **không bao giờ commit file này**.

| Biến | Bắt buộc | Ý nghĩa / cách đặt |
| --- | --- | --- |
| `ENVIRONMENT` | không (mặc định `development`) | `development` bật CORS cho Vite `localhost:5173`; giá trị khác tắt CORS (trừ khi đặt `CORS_ORIGINS`) |
| `CORS_ORIGINS` | không | Origin được phép gọi API, cách nhau bằng dấu phẩy (ví dụ tên miền thật khi triển khai). Không chấp nhận `*` |
| `POSTGRES_HOST` | không (mặc định `127.0.0.1`) | Dùng `127.0.0.1`, **không** dùng `localhost` (xem Xử lý sự cố) |
| `POSTGRES_PORT` | không (mặc định `5432`) | Đổi nếu cổng 5432 đã bị chiếm |
| `POSTGRES_USER` | có | Tên user DB, ví dụ `tutor` |
| `POSTGRES_PASSWORD` | **có** | Chuỗi ngẫu nhiên (lệnh ở trên) |
| `POSTGRES_DB` | có | DB chính, ví dụ `ai_language_tutor` |
| `POSTGRES_TEST_DB` | có | DB cho pytest, ví dụ `ai_language_tutor_test` (phải khác `POSTGRES_DB`) |
| `POSTGRES_CONNECT_TIMEOUT` | không (mặc định `10`) | Số giây chờ kết nối DB trước khi báo lỗi |
| `JWT_SECRET` | **có** | Chuỗi ngẫu nhiên ≥ 32 ký tự (lệnh ở trên). Thiếu hoặc ngắn hơn → backend không khởi động |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | không (mặc định `60`) | Thời hạn token đăng nhập, 1–1440 phút |
| `DEFAULT_LANGUAGE_CODE` | không (mặc định `en`) | Ngôn ngữ học của tài khoản mới; phải có `languages/<code>.yaml` |
| `LLM_PROVIDER` | không (mặc định `fake`) | `fake` = trả lời giả, không mạng, không tốn hạn mức (lượt `fake` không tính vào giới hạn ngày/toàn hệ thống, lưu `model_id` dạng `fake:...`); `gemini` = gọi Gemini thật (xem mục "Bật LLM thật"). Đổi sang `gemini` thì tạo cuộc trò chuyện mới |
| `LLM_MODEL_ID` | khi `LLM_PROVIDER=gemini` | Model chính. Đã kiểm chứng: `gemini-3.5-flash-lite`. Không dùng alias `*-latest` |
| `LLM_FALLBACK_MODEL_IDS` | không | Model dự phòng khi model chính hết hạn mức/quá tải, cách nhau bằng dấu phẩy (ví dụ `gemini-3.8-flash`) |
| `LLM_TIMEOUT_SECONDS` | không (mặc định `30`) | Thời gian chờ mỗi lần gọi, 1–120 giây |
| `LLM_MAX_RETRIES` | không (mặc định `1`) | Số lần thử lại cho lỗi tạm thời, 0–3 (ít để tiết kiệm hạn mức) |
| `LLM_MAX_OUTPUT_TOKENS` | không (mặc định `1024`) | Giới hạn token trả lời (gồm cả token "suy nghĩ" của Gemini) |
| `GEMINI_THINKING_LEVEL` | không (mặc định `low`) | `minimal` / `low` / `medium` / `high`, để trống = mặc định của model |
| `GEMINI_API_KEY` | khi `LLM_PROVIDER=gemini` | Tạo tại Google AI Studio. **Chỉ đặt trong `.env`**, không bao giờ trong `.env.example` hay mã nguồn |
| `CHAT_HISTORY_TURNS` | không (mặc định `10`) | Số lượt gần nhất gửi cho LLM (1 lượt = câu hỏi + trả lời; lượt lỗi không gửi), 0–50 |
| `CHAT_MAX_MESSAGE_CHARS` | không (mặc định `2000`) | Độ dài tối đa mỗi tin người dùng, 1–10000 ký tự; dài hơn → `422 message_too_long` |
| `CHAT_USER_PER_MINUTE` | không (mặc định `6`) | Tin chat mỗi phút mỗi người; vượt → `429 chat_rate_limited`. `0` = tắt |
| `CHAT_USER_PER_DAY` | không (mặc định `40`) | Tin chat mỗi ngày (theo `USER_TIMEZONE`) mỗi người; vượt → `429 chat_daily_limit_reached`. Lượt hỏng do hệ thống không tính |
| `CHAT_MAX_CONCURRENT_PER_USER` | không (mặc định `1`) | Số tin chờ trả lời cùng lúc mỗi người; vượt → `409 chat_busy` |
| `LLM_GLOBAL_PER_MINUTE` | không (mặc định `10`) | Lượt gọi LLM mỗi phút **toàn hệ thống** (một key chung); vượt → `429 service_busy` |
| `LLM_GLOBAL_PER_DAY` | không (mặc định `0` = tắt) | Lượt gọi LLM mỗi ngày toàn hệ thống. Đặt thấp hơn RPD thật trong AI Studio |
| `AUTH_LOGIN_FAILS_PER_EMAIL`, `AUTH_LOGIN_FAILS_PER_IP` | không (`5`, `20`) | Số lần đăng nhập sai trong cửa sổ; vượt → `429 auth_rate_limited` |
| `AUTH_LOGIN_WINDOW_SECONDS` | không (`900`) | Cửa sổ đếm đăng nhập sai, 60–86400 giây |
| `AUTH_REGISTER_PER_IP_PER_HOUR` | không (`10`) | Số lần đăng ký mỗi giờ mỗi IP |
| `USER_TIMEZONE` | không (`Asia/Ho_Chi_Minh`) | Ranh giới "ngày" cho giới hạn theo ngày |
| `TRUSTED_PROXY_COUNT` | không (`0`) | Số proxy tin cậy; `0` = không đọc `X-Forwarded-For`. Chỉ đổi khi triển khai sau proxy (Tuần 8) |
| `EMBEDDING_MODEL`, `QDRANT_URL` | chưa dùng | Dành cho Tuần 4 |

Frontend (tùy chọn): `frontend/.env.example` có `VITE_API_BASE_URL` (mặc định `http://127.0.0.1:8000/api/v1`). Chỉ cần tạo `frontend/.env.local` khi đổi địa chỉ backend. Biến `VITE_*` bị nhúng vào trang web công khai — không đặt secret ở đó.

## 3. PostgreSQL (Docker)

```powershell
docker compose up -d --wait        # lần đầu tải image postgres:18-alpine (~100 MB)
docker compose ps                  # postgres: Up ... (healthy)
```

- Lần khởi tạo đầu tiên tự tạo cả DB chính và DB test (`docker/postgres/init/`).
- Dữ liệu nằm trong volume Docker `pgdata`, còn nguyên khi tắt máy. `docker compose down` dừng DB và **giữ** dữ liệu; `docker compose down -v` **xóa toàn bộ dữ liệu**.
- Mật khẩu chỉ được áp dụng khi volume còn trống. Đổi `POSTGRES_PASSWORD` sau lần chạy đầu sẽ không đổi mật khẩu trong DB (phải đổi bằng SQL, hoặc `down -v` nếu chấp nhận mất dữ liệu).

## 4. Migration

Chạy từ thư mục `backend/`:

```powershell
cd backend
alembic upgrade head               # DB chính
alembic -x db=test upgrade head    # DB test (cần cho pytest)
alembic current                    # → 58871d077b8e (head)
cd ..
```

Xem trước SQL mà không chạm DB: `alembic upgrade head --sql`.

## 5. Backend

```powershell
uvicorn app.main:app --app-dir backend --reload --reload-dir backend
```

- http://127.0.0.1:8000/docs — thử API (có sẵn ví dụ hợp lệ; sau khi đăng nhập bấm **Authorize** và dán `access_token`).
- http://127.0.0.1:8000/health → `{"status":"ok"}`.
- Địa chỉ gốc http://127.0.0.1:8000 tự chuyển sang `/docs` (backend chỉ là API, không có trang riêng).

| API | Mô tả |
| --- | --- |
| `POST /api/v1/auth/register` | Tạo tài khoản + hồ sơ. Mật khẩu 8–128 ký tự, không trùng email |
| `POST /api/v1/auth/login` | Trả `access_token` (Bearer) |
| `GET /api/v1/profile/me` | Xem hồ sơ của mình (cần token) |
| `PATCH /api/v1/profile/me` | Sửa tên hiển thị, mục tiêu, trình độ (A1/A2/B1) |
| `GET /api/v1/languages/{code}` | Danh sách trình độ hợp lệ từ `languages/<code>.yaml` (không cần token) |

### Bật LLM thật (Gemini)

Mặc định `LLM_PROVIDER=fake`: không gọi mạng. Để dùng Gemini thật:

1. Tạo API key tại Google AI Studio. Đặt vào `.env` (dòng `GEMINI_API_KEY=...`) — **không** dán vào `.env.example`, chat, issue hay mã nguồn.
2. Trong `.env`, đặt `LLM_PROVIDER=gemini`, `LLM_MODEL_ID=gemini-3.5-flash-lite`, `LLM_FALLBACK_MODEL_IDS=gemini-3.8-flash`, `GEMINI_THINKING_LEVEL=low`.
3. Kiểm tra bằng **một** lời gọi thật (smoke test, mặc định bị bỏ qua):

   ```powershell
   $env:RUN_LLM_SMOKE = "1"; $env:LLM_SMOKE_CASE = "text"   # hoặc "structured"
   pytest backend/tests/test_llm_smoke.py -s
   Remove-Item Env:RUN_LLM_SMOKE, Env:LLM_SMOKE_CASE
   ```

Lưu ý gói miễn phí: Google có thể dùng nội dung gửi lên để cải thiện sản phẩm và người đánh giá có thể đọc nội dung đó; không gửi thông tin cá nhân. Chi tiết và nguồn: `docs/ENVIRONMENT_CHECK.md` (mục điều khoản dữ liệu). Hạn mức thật xem trong AI Studio (tài liệu không công bố con số cố định).

## 6. Frontend

Mở terminal thứ hai:

```powershell
cd frontend
npm ci                             # cài đúng phiên bản trong package-lock.json
npm run dev                        # → http://localhost:5173 (hoặc http://127.0.0.1:5173)
```

Giao diện tiếng Việt: đăng ký → đăng nhập → hồ sơ (chọn trình độ từ danh sách) → đăng xuất. Token lưu trong `sessionStorage` (mất khi đóng tab). Vite được ghim cổng 5173: nếu cổng bận, lệnh báo lỗi thay vì tự đổi sang cổng khác (cổng khác sẽ bị CORS chặn).

## 7. Kiểm thử

```powershell
pytest                                     # cần DB đang chạy và DB test đã migrate (bước 3–4)
python scripts/validate_dataset.py         # dataset ngữ pháp
python scripts/validate_evaluation.py      # bộ đánh giá placement/RAG
cd frontend; npm run build; cd ..          # kiểm tra TypeScript + build production
```

- Test API chạy trên **DB test**, mỗi test tự rollback: không đụng dữ liệu thật.
- Nếu PostgreSQL chưa chạy, các test cần DB được **bỏ qua** (skipped) thay vì treo; nếu DB test chưa migrate, pytest báo lỗi kèm lệnh cần chạy.
- Test LLM **không cần mạng và không cần key**: dùng `FakeLLM` và SDK Gemini với HTTP giả. Smoke test gọi API thật luôn bị bỏ qua trừ khi đặt `RUN_LLM_SMOKE=1`.

## Xử lý sự cố

| Hiện tượng | Nguyên nhân | Cách xử lý |
| --- | --- | --- |
| Kết nối DB chậm ~8 giây hoặc treo | `localhost` trên Windows thử IPv6 `::1` trước, Docker chỉ mở IPv4 | Đặt `POSTGRES_HOST=127.0.0.1` |
| Backend không khởi động: `JWT_SECRET chưa được đặt` | Thiếu hoặc secret < 32 ký tự | Sinh lại theo bước 2 |
| `422 Unprocessable Content` | Dữ liệu gửi lên chưa hợp lệ | Terminal backend ghi ô bị lỗi (`-> password: value_error`); lý do chi tiết ở Response body trên `/docs` |
| `401` sau một thời gian dùng | Token hết hạn (mặc định 60 phút) | Đăng nhập lại |
| `docker compose up` báo cổng 5432 đã dùng | Có PostgreSQL khác trên máy | Đổi `POSTGRES_PORT` trong `.env` |
| `npm run dev`: `Port 5173 is already in use` | Một Vite khác (hoặc ứng dụng khác) đang dùng cổng | Tắt tiến trình đó; nếu buộc phải đổi cổng, sửa `frontend/vite.config.ts` và thêm origin mới vào `CORS_ORIGINS` |
| Trình duyệt báo lỗi CORS | Frontend không chạy ở `localhost:5173`/`127.0.0.1:5173`, hoặc `ENVIRONMENT` khác `development` | Chạy `npm run dev` mặc định; kiểm tra `ENVIRONMENT`, hoặc thêm origin vào `CORS_ORIGINS` |

## Cấu trúc

| Thư mục | Nội dung |
| --- | --- |
| `backend/app/` | FastAPI: `core/` (cấu hình, bảo mật, lỗi), `db/`, `models/`, `schemas/`, `services/`, `api/` |
| `backend/alembic/` | Migration cơ sở dữ liệu |
| `backend/tests/` | pytest (API, ràng buộc DB, dataset) |
| `frontend/` | Vite + React + TypeScript + Tailwind |
| `languages/` | Cấu hình ngôn ngữ và trình độ (`en.yaml`) |
| `data/` | Dataset ngữ pháp, bộ đánh giá; `data/archive/` là bản gốc không sửa |
| `docs/` | Kế hoạch, kiến trúc, thiết kế DB, nhật ký kiểm chứng môi trường |
| `scripts/` | Kiểm tra môi trường, validate dữ liệu |
| `docker/` | Script khởi tạo PostgreSQL |
