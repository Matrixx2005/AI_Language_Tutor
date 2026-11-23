# Kết quả kiểm tra môi trường

<!-- check_env:AUTO_START -->
## Kết quả tự động (scripts/check_env.py)

Chạy lúc: 2026-11-20 21:06

| Mục | Kết quả |
| --- | --- |
| Python đang chạy | 3.13.11 |
| Đường dẫn Python | F:\AI_Language_Tutor\.venv\Scripts\python.exe |
| Đang trong venv | có |
| Yêu cầu Python >= 3.13 | ĐẠT |
| Hệ điều hành | Windows 11 (AMD64) |
| RAM | 31.6 GB tổng, 13.7 GB trống |
| Ổ đĩa dự án trống | 295.5 GB |
| git | git version 2.54.0.windows.1 |
| node | v24.15.0 |
| npm | 11.12.1 |
| docker | Docker version 29.9.3, build 5457199 |
| docker compose | Docker Compose version v5.7.0 |
| Các bản Python (py -0p) | *               F:\AI_Language_Tutor\.venv\Scripts\python.exe |
| Python trong .venv | Python 3.13.11 |
<!-- check_env:AUTO_END -->

## Đính chính so với lần chạy 2026-11-18 20:27

- Lần chạy đó dùng Python hệ thống (`Đang trong venv: KHÔNG`), không phải `.venv`.
- `npm: KHÔNG TÌM THẤY` là **báo sai**: script cũ gọi `subprocess.run(["npm", ...])`, cách này trên Windows không tìm thấy `npm.cmd`. Kiểm tra lại cùng ngày: `npm --version` → `11.12.1`. Script đã được sửa để dùng `shutil.which`.
- Docker và Docker Compose: kiểm tra lại vẫn **không tìm thấy** (đúng).

## Buổi 2 — Repo và tương thích

Kiểm tra tiếp: 2026-11-18

### Repo

- Đã tạo `.venv` bằng Python 3.13.11; pip 25.3.
- Hiện có: `backend/app/`, `backend/tests/`, `data/processed/`, `data/evaluation/`, `docs/`, `languages/`, `prompts/en/`, `scripts/`, `.env.example`, `.gitignore`, `pytest.ini`.
- Chưa có: frontend, cấu hình package/dependency (requirements/pyproject, package.json), `experiments/`.
- Thư mục dự án **chưa phải Git repository** (`git status` → `fatal: not a git repository`). Chưa khởi tạo Git.
- Không có sơ đồ thư mục chi tiết của “Master Prompt” trong workspace để đối chiếu; chưa tự tạo thêm cấu trúc theo suy đoán.

### Kiểm thử

- Đã cài pytest 9.2.0 trong `.venv` sau khi được cho phép.
- Đã thêm `pytest.ini` (`pythonpath = .`). Trước đó gõ `pytest` trực tiếp thì lỗi `ModuleNotFoundError: No module named 'scripts'`; chỉ `python -m pytest` chạy được.
- Lệnh: `.venv\Scripts\python.exe -m pytest -q` hoặc `.venv\Scripts\pytest.exe -q`.
- Kết quả gần nhất: xem mục "Kiểm chứng lần cuối" bên dưới.
- FastAPI/Pydantic chưa được cài vào `.venv`; các test hiện tại không cần hai gói này.

### Dry-run tương thích Python 3.13

Các lệnh `pip install --dry-run` hoàn tất thành công, không thấy lỗi tương thích khi resolver tìm bản phân phối cho Windows/Python 3.13:

| Gói | Phiên bản resolver chọn |
| --- | --- |
| torch | 2.15.0 |
| sentence-transformers | 6.3.0 |
| qdrant-client | 1.20.0 |
| rank_bm25 | 0.2.2 |

Lệnh kiểm tra `qdrant-client`/`rank_bm25`: `.venv\Scripts\python.exe -m pip install --dry-run qdrant-client rank_bm25`

Lệnh kiểm tra PyTorch/embedding: `.venv\Scripts\python.exe -m pip install --dry-run torch sentence-transformers`

Dry-run đã truy vấn index và lấy metadata gói; không cài các gói trên, không tải model BGE-M3. Đây chỉ xác nhận resolver tìm được bản phân phối, chưa xác nhận runtime/import hoặc hiệu năng CPU.

## Kiểm chứng lần cuối

2026-11-18 21:08, chạy bằng `.venv` (Python 3.13.11):

| Lệnh | Kết quả |
| --- | --- |
| `.venv\Scripts\pytest.exe -q` | `9 passed in 0.02s` (sau khi thêm test vị trí đáp án) |
| `.venv\Scripts\python.exe scripts/validate_dataset.py` | `Validation passed: 15 records, 0 errors.` |
| `.venv\Scripts\python.exe scripts/validate_evaluation.py` | `Evaluation validation passed: 30 placement questions, 30 RAG queries, 20 dev / 10 test.` |

## Tuần 2 — Buổi 1 (2026-11-18)

- Cài vào `.venv` sau khi người dùng cho phép: `pip install -r backend/requirements-dev.txt` (lần đầu lỗi mạng `ConnectionResetError 10054`, chạy lại với `--retries 10` thành công). Kiểm tra import: fastapi 0.164.0, SQLAlchemy 2.1.9, psycopg 3.3.9 (impl `binary`), băm `argon2id` qua pwdlib hoạt động.
- `uvicorn app.main:app --app-dir backend`: `GET /health` → `200 {"status":"ok"}`.
- `pytest`: 13 passed, 1 cảnh báo (Starlette khuyến nghị `httpx2` thay `httpx` cho TestClient).
- Docker/Docker Compose: vẫn chưa có. `docker-compose.yml` mới kiểm tra cú pháp YAML, **chưa chạy được**. Người dùng chọn phương án A (Docker Desktop + WSL2).

## Tuần 2 — Docker và PostgreSQL (2026-11-20)

- Người dùng cài Docker Desktop: `docker run hello-world` thành công; Docker 29.9.3, Docker Compose v5.7.0.
- `docker compose up -d --wait` → container `postgres` healthy, cổng `127.0.0.1:5432`. PostgreSQL 18.7; có DB `ai_language_tutor` và `ai_language_tutor_test` (script init tạo); dữ liệu nằm ở `/var/lib/postgresql/18` trong volume.
- Lỗi phát hiện và đã sửa: kết nối tới `localhost` mất 8,02s (treo nếu không có timeout) do Windows thử IPv6 `::1` trước, trong khi Docker chỉ bind `127.0.0.1` (0,04s). Đổi `POSTGRES_HOST` mặc định thành `127.0.0.1` và thêm `connect_timeout=10`.
- Sau sửa: backend kết nối DB chính 0,16–0,19s, DB test OK; khi tắt DB, lỗi `OperationalError` sau 10,1s thay vì treo. `pytest`: 13 passed.

## Tuần 2 — Buổi 2 (2026-11-20)

- Models `users`, `learner_profiles` và migration `58871d077b8e` (Alembic autogenerate). SQL xem trước bằng `alembic upgrade head --sql` (không chạm DB).
- Lưu ý: `alembic revision --autogenerate` (Alembic 1.20.1) tạo bảng rỗng `alembic_version` trong DB khi so sánh schema. Đã xóa bảng rỗng này để DB trở lại trống (0 bảng) trước khi người dùng duyệt migration.
- Lỗi phát hiện và đã sửa: `.gitignore` dòng `models/` chặn cả `backend/app/models/`; đổi thành `/models/` (chỉ thư mục model AI ở gốc).
- `pytest` sau khi viết models: 19 passed (6 test models không cần DB).
- Người dùng cho phép chạy migration và giữ default `A1` theo ERD (phương án a).
  - DB chính: `alembic upgrade head` → `58871d077b8e (head)`; `alembic check` → `No new upgrade operations detected.`
  - DB test: upgrade → downgrade base (còn `alembic_version`) → upgrade lại, đều sạch; `alembic -x db=test check` → không lệch.
- Thêm `backend/tests/conftest.py` (fixture DB test, rollback mỗi test) và `test_db_schema.py` (6 test ràng buộc thật trong PostgreSQL: default ERD, trùng email, email chưa chuẩn hóa, RESTRICT khi xóa user, FK bắt buộc).
- `pytest`: **25 passed**, 1 cảnh báo httpx. Sau khi chạy: DB test 0 dòng; DB chính `users` 0 dòng.

## Tuần 2 — Buổi 3 (2026-11-20)

- Người dùng cho phép thêm `JWT_SECRET` (sinh ngẫu nhiên, 86 ký tự) và `ACCESS_TOKEN_EXPIRE_MINUTES=60` vào `.env`; `.env.example` có biến trống kèm hướng dẫn. Không cài thêm gói.
- `pytest`: **69 passed**, 1 cảnh báo httpx. DB test và DB chính đều 0 user sau khi chạy.
- Kiểm tra độ chặt của test bằng cách cố ý làm hỏng code: bỏ kiểm tra loại token → test đỏ; bỏ băm giả/đổi thông báo lỗi đăng nhập → test đỏ; trả lại `input` trong lỗi 422 → ban đầu test **không** bắt được, đã bổ sung trường hợp lỗi nằm ở chính ô mật khẩu, sau đó test đỏ đúng.
- Server thật (uvicorn): 401 `not_authenticated` / `invalid_token` / `invalid_credentials`, 422 đúng định dạng; log server không chứa mật khẩu đã gửi.

## Tuần 2 — Buổi 4 (2026-11-20)

- `frontend/`: Vite 7.3.8, React 19.3.1, TypeScript 5.9.3, Tailwind CSS 4.3.5, React Router 7.18.6. `npm run build` → **pass** (`tsc -b` và `vite build`; 1.702 modules được transform). Build tạo `frontend/dist/` (đã được Git ignore).
- Test CORS mới (`backend/tests/test_cors.py`): origin dev `http://localhost:5173` được phản hồi `Access-Control-Allow-Origin`; origin lạ không có header này; khi `ENVIRONMENT=production`, CORS không được bật. Toàn bộ `pytest backend/tests` → **72 passed**, 2 cảnh báo (Starlette/httpx deprecation và pytest cache không ghi được do quyền thư mục).
- Chạy backend dev server tại `127.0.0.1:8000` với `POSTGRES_DB` trỏ tới DB test; Vite dev server tại `127.0.0.1:5173`. HTTP GET trang Vite trả 200 và header CORS đúng. Luồng HTTP qua hai server: đăng ký 201 → đăng nhập 200 → xem hồ sơ 200 → sửa hồ sơ 200 → đọc lại dữ liệu đã sửa 200. Token hết hạn trả `401 token_expired`; token sai trả `401 invalid_token`. Tài khoản thử nghiệm được tạo trong DB test rồi xóa sau khi kiểm tra.
- **Giới hạn kiểm chứng:** chưa thao tác được luồng trên giao diện trình duyệt. Công cụ điều khiển Chrome timeout khi xin quyền truy cập hai lần. Vì thế đăng xuất qua nút giao diện và điều hướng thực tế về trang đăng nhập chưa được kiểm tra runtime; mã hiện xóa token phía client trong `sessionStorage` rồi điều hướng `/login`.
- **Quyết định lưu token:** dùng `sessionStorage` để token còn sau khi reload nhưng tự mất khi đóng phiên/tab trình duyệt. Đánh đổi: JavaScript trang vẫn đọc được token, nên XSS có thể đánh cắp token; đây là lựa chọn phù hợp cho nền hiện tại nhưng không thay thế biện pháp chống XSS.
- **Kiểm chứng trên trình duyệt — do người dùng tự thực hiện (2026-11-21):** người dùng báo đã tự thử giao diện trên trình duyệt: đăng ký, đăng nhập, sửa hồ sơ, tải lại trang, đăng xuất — kết quả ổn. Claude không quan sát trực tiếp phiên này; đây là kết quả do người dùng tự kiểm chứng và tự báo cáo. Bổ sung cho giới hạn kiểm chứng ghi ở trên.

## Tuần 2 — Buổi 5 (2026-11-21): kiểm thử toàn tuyến

Do Claude chạy, kết quả thật:

| Kiểm tra | Lệnh | Kết quả |
| --- | --- | --- |
| Test backend | `pytest` | `78 passed, 1 warning` (cảnh báo Starlette/httpx) |
| Test khi DB tắt | `docker compose stop` rồi `pytest -rs` | `34 passed, 44 skipped` trong ~6s, không treo; bật lại → 78 passed |
| Build frontend | `npm run build` | `tsc -b` + `vite build` pass, 1.702 modules, exit 0 |
| Gói frontend khớp lockfile | `npm ls --depth=0` | exit 0; vite 7.3.8, react 19.3.1, react-router-dom 7.18.6, typescript 5.9.3, tailwindcss 4.3.5 |
| Migration từ DB trống | `alembic -x db=test downgrade base` → `upgrade head` → `check` | sạch; `No new upgrade operations detected.` |
| DB chính | `alembic current`, `alembic check` | `58871d077b8e (head)`, không lệch |
| Secret trong repo | dò giá trị thật `POSTGRES_PASSWORD`, `JWT_SECRET` trong thư mục làm việc, **toàn bộ 8 commit**, `frontend/dist`; dò mẫu key | không có |
| `.env` và Git | `git ls-files`, `git check-ignore` | `.env`, `frontend/.env`, `frontend/.env.local` bị ignore; chỉ `*.env.example` được theo dõi |

- `.env.example`: bổ sung `ENVIRONMENT` (điều khiển CORS) và `POSTGRES_CONNECT_TIMEOUT` (tùy chọn); `QDRANT_URL` đổi sang `127.0.0.1`. Không có giá trị thật.
- Bỏ một test CORS trùng trong `test_api_docs_and_logging.py` (đã có đầy đủ hơn ở `test_cors.py`, gồm cả trường hợp production).
- **Chưa kiểm chứng:** `npm ci` trên bản clone sạch (chưa chạy để không cài lại `node_modules` khi chưa được phép).

### Buổi 5 — hoàn tất tồn đọng trước commit (2026-11-21)

- **Ô trình độ:** thêm `GET /api/v1/languages/{code}` (đọc `languages/<code>.yaml`, không cần token, không lộ ngưỡng placement); trang hồ sơ đổi ô nhập tự do thành danh sách chọn lấy từ API này.
- **CORS:** thêm `CORS_ORIGINS` (danh sách origin, chặn `*`); để trống thì giữ hành vi cũ (development → Vite, khác → tắt).
- **Vite:** phát hiện trên Windows Vite mặc định chỉ nghe `::1` → `http://127.0.0.1:5173` không mở được (`URLError`), `localhost` thì được. Ghim `host 127.0.0.1`, `port 5173`, `strictPort`. Sau sửa: cả `localhost:5173` và `127.0.0.1:5173` → 200; khi cổng bận → `Error: Port 5173 is already in use`, exit 1, không chạy ở cổng khác.
- **Thử README trên bản sao sạch** (chép đúng các file sẽ commit — không có `.env`, `.venv`, `node_modules` — sang thư mục tạm; PostgreSQL riêng ở cổng 5433, project `fresh-clone`, không đụng DB đang dùng):

| Bước README | Kết quả |
| --- | --- |
| 1. venv Python 3.13 + `pip install -r backend/requirements-dev.txt` | Python 3.13.11, pip exit 0 |
| 2. `.env` từ `.env.example` + sinh secret (đổi `POSTGRES_PORT=5433` theo mục Xử lý sự cố) | OK |
| 3. `docker compose up -d --wait` | `fresh-clone-postgres-1` healthy, `127.0.0.1:5433` |
| 4. `alembic upgrade head` + `-x db=test upgrade head` | `58871d077b8e (head)` |
| 5. Backend uvicorn | register 201 → login 200 → profile 200 (en/A1) → languages 200 (A1/A2/B1) → PATCH A2 200 → PATCH C2 422 `invalid_level_code`; CORS cho `localhost:5173` |
| 6. `npm ci` + `npm run build` + `npm run dev` | 88 gói, exit 0; build pass; trang Vite 200 |
| 7. `pytest` + 2 validator | 85 passed; 15 records 0 errors; 30/30, 20 dev / 10 test |

  Sau kiểm tra: `docker compose down -v` chỉ trên project `fresh-clone` (đã xác nhận tên trước khi chạy), xóa thư mục tạm; volume `ai_language_tutor_pgdata` và DB đang dùng còn nguyên (healthy, 1 user).
- **Chưa kiểm chứng:** giao diện danh sách chọn trình độ trên trình duyệt (Claude chỉ kiểm chứng qua build TypeScript và API). Bản sao chạy trên chính máy này (pip/npm dùng cache), chưa thử trên máy khác.
- `pytest` cuối cùng trên repo: **85 passed**, 1 cảnh báo httpx; `npm run build` pass.
- Địa chỉ gốc `/` của backend chuyển hướng 307 sang `/docs` (người dùng hai lần mở `/` và gặp 404). `pytest`: **86 passed**.
- **Kiểm chứng trên trình duyệt — do người dùng tự thực hiện (2026-11-21):** sau khi khởi động lại backend và Vite theo hướng dẫn, người dùng báo "đã test ok hết": `GET /api/v1/languages/en` trả danh sách trình độ; trang hồ sơ hiện ô trình độ dạng danh sách chọn (A1/A2/B1 kèm tên tiếng Việt); chọn và lưu trình độ, tải lại trang, mở bằng `127.0.0.1:5173`, đăng xuất đều ổn. Claude không quan sát trực tiếp phiên này; đây là kết quả do người dùng tự kiểm chứng và tự báo cáo.

## Tuần 3 — Bước 0–2 (2026-11-21)

Do Claude chạy: `pytest` 86 passed; `npm run build` pass; `alembic check` (DB chính và DB test) không lệch; `.env` có dòng `GEMINI_API_KEY` nhưng **trống** lúc đó. Tài liệu Gemini đã đọc (trang ngày 2026-11-21, `ai.google.dev` chuyển hướng sang `aistudio.google.com`): `/docs/models`, `/docs/deprecations`, `/docs/libraries`, `/docs/structured-output`, `/docs/rate-limits`, `/docs/pricing`, `/docs/terms`, `/docs/billing`, `/docs/available-regions`, `/docs/text-generation`, `/docs/safety-settings`, `/docs/troubleshooting`, `/docs/api-errors`, PyPI `google-genai` (3.6.1, Python ≥3.11) và `google-generativeai` (ngừng hỗ trợ 30/11/2025), `google/genai/errors.py`. Tài liệu không công bố hạn mức gói miễn phí cho model Flash; chỉ xem được trong AI Studio của tài khoản.

Người dùng chốt: làm theo đề xuất 1–10; dùng key gói miễn phí, yêu cầu tối ưu hạn mức.

## Tuần 3 — Buổi 1: lớp LLM và LLM giả (2026-11-23)

- **Sự cố key:** người dùng dán API key thật vào cả `.env` và `.env.example` (file được Git theo dõi). Claude kiểm tra (không in key): key **không** có trong 10 commit, không có trên `origin/main`, chưa được stage; hai key giống nhau. Được người dùng cho phép, Claude xóa giá trị key khỏi `.env.example` (`git diff` sau đó rỗng); `.env` giữ nguyên key. Nội dung key đã hiện trong phiên làm việc qua thông báo thay đổi file; khuyến nghị (không bắt buộc) tạo key mới.
- Docker Desktop không chạy (máy khởi động lại): lần chạy đầu `75 passed, 44 skipped`. Claude mở Docker Desktop (cài theo user tại `%LOCALAPPDATA%\Programs\DockerDesktop`), `docker compose up -d --wait` → healthy; dữ liệu còn nguyên (1 user).
- Tạo `backend/app/llm/`: `errors.py` (7 lỗi chuẩn hóa, có `retryable`/`fallback_allowed`), `types.py`, `provider.py` (giao diện), `service.py` (timeout tổng, thử lại có giới hạn + backoff có jitter, tôn trọng `retry_after` tối đa 8s, model dự phòng, kiểm tra structured output, log chỉ metadata), `fake.py` (FakeLLM lập trình được), `providers.py` (danh bạ duy nhất biết tên nhà cung cấp; `gemini` chưa cài đặt → `LLMConfigError`), `__init__.py` (`build_llm_service`, `get_llm_service` tạo lười).
- Cấu hình mới (mặc định an toàn `LLM_PROVIDER=fake`, `LLM_MAX_RETRIES=1`): `LLM_MODEL_ID`, `LLM_FALLBACK_MODEL_IDS`, `LLM_TIMEOUT_SECONDS`, `LLM_MAX_RETRIES`, `LLM_MAX_OUTPUT_TOKENS`; `.env.example` cập nhật (không giá trị bí mật). `.env` **chưa sửa**.
- `pytest backend/tests/test_llm_service.py`: 33 passed. Làm hỏng code có chủ đích (rồi khôi phục, `cmp` xác nhận nguyên vẹn): thử lại mọi lỗi → 10 failed; fallback cho mọi lỗi → 1 failed; bỏ kiểm tra schema → 4 failed; luôn chờ `retry_after` dài → 2 failed.
- Toàn bộ `pytest` (DB chạy): **119 passed**, 1 cảnh báo httpx (đã biết, xử lý ở Buổi 2 cùng SDK dùng httpx2). `alembic check`: không lệch.
- **Chưa kiểm chứng:** hành vi với nhà cung cấp thật (Buổi 2). Timeout tổng dùng thread: lời gọi quá hạn vẫn chạy nền đến khi provider tự hủy theo `timeout_seconds` — provider thật phải tôn trọng tham số này.

## Tuần 3 — Buổi 2: nhà cung cấp Gemini (2026-11-23)

### Claude đã chạy

- `.env`: `GEMINI_API_KEY` **có** (key người dùng tạo lại); không có trong `.env.example`, file sẽ commit hay 10 commit lịch sử. `LLM_MODEL_ID` trong `.env` **trống** — không sửa `.env`; lời gọi thật truyền model qua biến môi trường của lệnh.
- `pip install --dry-run` rồi (người dùng cho phép) `pip install google-genai==3.6.1`: Python 3.13.11; kéo theo 13 gói (httpx2 2.16.2, google-auth 2.63.1, tenacity 9.1.4, ...). `pip check`: không lỗi. `requirements.txt`: thêm `google-genai==3.6.1`, `httpx2==2.16.2`; `requirements-dev.txt`: bỏ `httpx` (không gói nào còn cần). Cảnh báo `httpx` của Starlette **đã hết** (Starlette tự dùng httpx2).
- Đối chiếu mã nguồn SDK đã cài: `HttpOptions.timeout` tính bằng **mili giây** (truyền xuống httpx + header `X-Server-Timeout`); không có `retry_options` thì SDK không thử lại (vẫn đặt `attempts=1` tường minh); key gửi qua header `x-goog-api-key`, không nằm trong URL; `generate_content` còn hỗ trợ; token ở `usage_metadata.prompt_token_count / candidates_token_count / thoughts_token_count`, model ở `model_version`.
- `backend/app/llm/gemini.py`: `GeminiProvider` (module duy nhất đọc `GEMINI_API_KEY`, qua `GeminiSettings`), timeout mỗi lời gọi, ánh xạ lỗi (429 theo `QuotaFailure` PerDay → hết hạn mức, còn lại → giới hạn tạm thời, đọc `RetryInfo.retryDelay`; 402 → hết hạn mức; 400/401/403/404 → cấu hình; 408/504 → hết thời gian; 5xx → máy chủ; chặn an toàn qua `prompt_feedback.block_reason` và `finish_reason`), `GEMINI_THINKING_LEVEL` (mặc định `low`). Đăng ký trong `providers.py`. `LLMService` áp `LLM_MAX_OUTPUT_TOKENS` mặc định.
- `backend/tests/test_llm_gemini.py`: 41 test chạy **code thật của SDK** với `httpx2.MockTransport` (không mạng). `backend/tests/test_llm_smoke.py`: đúng một smoke test, mặc định bỏ qua (`RUN_LLM_SMOKE=1` mới chạy).
- Không mạng, không key: `GEMINI_API_KEY="" LLM_PROVIDER=fake HTTP(S)_PROXY=http://127.0.0.1:9 pytest` → **162 passed, 1 skipped** (smoke).
- Làm hỏng code có chủ đích (khôi phục, `cmp` xác nhận): bỏ timeout SDK → 1 failed; hết hạn mức ngày bị coi là tạm thời → 2 failed; key lọt vào `repr` → 1 failed; bật lại retry của SDK (`attempts=3`) → 13 failed. Một test ban đầu viết lỏng (`assert ... or ...`) đã được sửa thành kiểm tra chặt.
- **Gọi API thật (người dùng cho phép, 3/3 lượt, mỗi lượt 1 request, không thử lại, không model dự phòng):**

| Lượt | Model | Thinking | Kết quả thật |
| --- | --- | --- | --- |
| 1 | `gemini-3.8-flash` | mặc định (medium) | `504 DEADLINE_EXCEEDED` sau ~29,6s → `llm_timeout` (đúng ánh xạ) |
| 2 | `gemini-3.8-flash` | `low` | `503 UNAVAILABLE` sau ~4s → `llm_provider_error` (đúng ánh xạ) |
| 3 | `gemini-3.5-flash-lite` | `low` | **200 OK**, model thực tế `gemini-3.5-flash-lite`, độ trễ **1372 ms**, token vào/ra **42/51**, 1 lần gọi |

  Cả 3 lượt: chạy với log mức DEBUG (httpx2, SDK, app) — **key không xuất hiện** trong output/log. URL bị log chỉ chứa tên model.
- Quét secret (thư mục làm việc + 10 commit): `GEMINI_API_KEY`, `POSTGRES_PASSWORD`, `JWT_SECRET` không có; không mẫu key Google trong file sẽ commit; `.env` không bị Git theo dõi.
- `pytest` cuối (DB chạy, chế độ bình thường): **162 passed, 1 skipped**, không cảnh báo; `alembic check` không lệch.

### Chưa kiểm chứng

- Structured output với API thật (hết lượt gọi cho phép); mới kiểm chứng qua SDK + MockTransport.
- `gemini-3.8-flash` chưa trả lời thành công lần nào (504 rồi 503) — chưa rõ do quá tải tạm thời hay giới hạn gói miễn phí.
- Ánh xạ 429 dựa trên cấu trúc lỗi Google (`QuotaFailure`, `RetryInfo`) trong test; chưa gặp 429 thật.
- Chất lượng câu trả lời: lượt 3 nói "dùng *an* trước nguyên âm u, e, o, a, i" — chưa chính xác (quy tắc theo **âm**, ví dụ *an hour*, *a university*). Cần xử lý trong prompt gia sư (Buổi 3) và RAG (Tuần 4).

## Tuần 3 — Buổi 2 (hoàn thiện, 2026-11-23)

### Claude đã chạy

- **Cờ cắt cụt:** thêm `truncated: bool` vào `ProviderResponse` và `LLMResult`; Gemini đặt `True` khi `finish_reason=MAX_TOKENS` mà vẫn có văn bản (văn bản vẫn trả về; structured output bị cắt vẫn là `llm_invalid_response`). Log `llm ok ...` có thêm `truncated=`. Phát hiện và sửa thêm: `ProviderResponse` trước đó dùng `repr` mặc định của dataclass → **in cả nội dung trả lời**; nay `repr` chỉ có metadata. 9 test mới. Làm hỏng code có chủ đích (khôi phục, `cmp` xác nhận): Gemini không bao giờ đánh dấu cắt → 2 failed; luôn đánh dấu cắt → 3 failed; LLMService làm rơi cờ → 2 failed; `ProviderResponse` dùng lại `repr` mặc định → 1 failed.
- **Model mặc định:** `.env.example` đổi sang `LLM_MODEL_ID=gemini-3.5-flash-lite`, `LLM_FALLBACK_MODEL_IDS=gemini-3.8-flash`, kèm chú thích trạng thái kiểm chứng. README: bảng biến `LLM_*`, `GEMINI_*` và mục "Bật LLM thật (Gemini)". `.env` **không sửa**.
- **Structured output thật** (người dùng đồng ý đúng 1 lời gọi; `LLM_SMOKE_CASE=structured`, `gemini-3.5-flash-lite`, `GEMINI_THINKING_LEVEL=low`, không thử lại, không dự phòng): **200 OK**, model thực tế `gemini-3.5-flash-lite`, độ trễ **1379 ms**, token vào/ra **35/41**, `truncated=False`, 1 lần gọi. Đối tượng đã parse: `ArticleAnswer(article='an', reason_vi="Dùng 'an' trước từ 'apple' vì nó bắt đầu bằng một nguyên âm ('a').")`. Nhận xét: đáp án `an` đúng; lý do dựa vào **chữ cái** chứ không phải **âm** (đúng với *apple*, sẽ sai nếu áp cho *university*/*hour*). Key không xuất hiện trong output/log DEBUG.
- **Nguồn gói** (đọc metadata đã cài): `google-genai` 3.6.1 — Google LLC `<googleapis-packages@google.com>`, Apache-2.0, `https://github.com/googleapis/python-genai`, `Requires-Python >=3.11`, `Requires-Dist` có `httpx2<3.0.0,>=2.0.0` (httpx2 là phụ thuộc khai báo chính thức). `httpx2` 2.16.2 — tác giả Tom Christie, bảo trì "Pydantic Services Inc.", BSD-3-Clause, `https://github.com/pydantic/httpx2`, phụ thuộc `httpcore2==2.16.2`, `anyio`, `idna`, `truststore`. `pip check`: `No broken requirements found.` Không thấy điểm đáng ngờ. Giới hạn: metadata do nhà phát hành tự khai; chưa đối chiếu chữ ký/attestation.
- `pytest` không mạng, không key (`GEMINI_API_KEY=""`, `LLM_PROVIDER=fake`, proxy HTTP trỏ cổng chết): **171 passed, 1 skipped** (smoke). Chạy bình thường: 171 passed, 1 skipped, không cảnh báo.
- Quét secret (thư mục làm việc + 10 commit): `GEMINI_API_KEY`, `POSTGRES_PASSWORD`, `JWT_SECRET` không có; `.env.example` không có giá trị key; `.env` không bị Git theo dõi; không mẫu key Google trong file sẽ commit.

### Điều khoản dữ liệu Gemini API (đọc lại 2026-11-23)

Nguồn: https://aistudio.google.com/docs/terms (chuyển hướng từ ai.google.dev/gemini-api/terms; "Effective March 23, 2026"), https://aistudio.google.com/docs/logs-policy, https://aistudio.google.com/docs/pricing. Chỉ ghi điều tài liệu nói.

| Nội dung | Gói miễn phí ("Unpaid Services") | Gói trả phí ("Paid Services") |
| --- | --- | --- |
| Dùng nội dung để cải thiện sản phẩm | **Có**: Google dùng nội dung gửi lên và câu trả lời "to provide, improve, and develop Google products and services and machine learning technologies" (terms). Trang giá ghi "Used to improve our products: Yes" cho 3.8 Flash, 3.6 Flash, 3.5 Flash-Lite | **Không**: "Google doesn't use your prompts ... or responses to improve our products" (terms). Ngoại lệ: "Contributor Tier" (thử nghiệm theo lời mời) áp dụng điều khoản của gói miễn phí |
| Lưu trữ | Terms **không nêu thời hạn** lưu prompt/câu trả lời. Grounding với Google Search/Maps: lưu 30 ngày | Google ghi log prompt/câu trả lời "for a limited period of time, solely for detecting and preventing violations" của Prohibited Use Policy và cho yêu cầu pháp lý — **không nêu số ngày**. Trang logs-policy: log dữ liệu API của nhà phát triển (dự án có billing) mặc định tối đa **55 ngày** (chỉnh 7/14/28/55), tách biệt với log chống lạm dụng |
| Người đánh giá con người | **Có**: "human reviewers may read, annotate, and process your API input and output"; Google tách dữ liệu khỏi tài khoản, API key, Cloud project trước khi người đánh giá xem | Terms **không nói** về người đánh giá cho dữ liệu trả phí. Logs-policy: người đánh giá có thể đọc log mà nhà phát triển **tự chia sẻ** (dataset/feedback) |
| Dữ liệu nhạy cảm | "Do not submit sensitive, confidential, or personal information to the Unpaid Services." | Terms không có câu tương tự; logs-policy yêu cầu không chia sẻ log chứa thông tin nhạy cảm |
| Khi nào là trả phí | — | Gemini API là trả phí "only when accessing the API through a Cloud Project associated with an active billing account" |

Quy định chung: người dùng API phải từ 18 tuổi; dịch vụ dành cho "professional or business purposes, not for consumer use". Ứng dụng phục vụ người dùng ở EEA, Thụy Sĩ, Vương quốc Anh chỉ được dùng gói trả phí.

**Chưa rõ (tài liệu không nêu):** thời hạn lưu log chống lạm dụng; thời hạn lưu dữ liệu của gói miễn phí; có tuyển chọn người đánh giá cho dữ liệu trả phí ngoài phần log tự chia sẻ hay không; có tùy chọn "zero data retention" hay không. Trang `/docs/usage-policies` chưa đọc.

**Hệ quả cho dự án:** key hiện là gói miễn phí → không gửi email/tên người dùng vào prompt; giao diện chat cần thông báo nội dung được gửi tới Google (quyết định 9, Buổi 6). Thử với người học thật nên dùng dự án có billing.

### Chưa kiểm chứng

- `gemini-3.8-flash` vẫn chưa trả lời thành công lần nào (504, 503 ở Buổi 2); chưa gọi lại.
- Chưa gặp lỗi 429 thật; ánh xạ 429 mới kiểm chứng bằng cấu trúc lỗi trong test.
- Cờ `truncated=True` chưa quan sát được với API thật (hai lời gọi thành công đều `STOP`).
- `.env` vẫn có `LLM_MODEL_ID` trống: người dùng cần tự đặt theo hướng dẫn trong báo cáo Buổi 2.

## Tuần 3 — Buổi 3: chat API, prompt gia sư, lưu lịch sử (2026-11-23)

### Claude đã chạy

- Kiểm tra `.env` sau khi người dùng sửa (không in key): `LLM_PROVIDER=gemini`, `LLM_MODEL_ID=gemini-3.5-flash-lite`, `LLM_FALLBACK_MODEL_IDS=gemini-3.8-flash`, `GEMINI_THINKING_LEVEL=low` đúng; không dòng trùng; key có. Dòng `GEMINI_API_KEY` có 1 khoảng trắng sau `=` (vẫn đọc đúng vì được loại bỏ khi nạp).
- Docker Desktop lại tắt giữa phiên → Claude mở lại; PostgreSQL healthy; DB chính còn 1 user.
- Tạo: `backend/app/services/chat_history.py` (hàm thuần cắt lịch sử: chỉ lượt hoàn chỉnh, bỏ lượt lỗi, giữ N lượt gần nhất), `prompts/en/tutor.md` (giải thích bằng tiếng Việt, ví dụ tiếng Anh, theo trình độ; quy tắc theo **âm** như *an hour*/*a university*; không dẫn nguồn; từ chối nhẹ khi lạc đề; không lộ system prompt), `backend/app/core/prompts.py` (nạp theo `language_code`, thiếu biến → lỗi), `backend/app/models/chat.py`, `backend/app/schemas/chat.py`, `backend/app/services/chat.py`, `backend/app/api/routes/chat.py`, dependency `get_llm` (thiếu cấu hình → 503 `llm_not_configured`). Cấu hình mới: `CHAT_HISTORY_TURNS` (10), `CHAT_MAX_MESSAGE_CHARS` (2000).
- API: `POST/GET /api/v1/chat/sessions`, `GET/POST /api/v1/chat/sessions/{id}/messages`. Phiên của người khác → 404 `chat_session_not_found`. Tin người dùng được commit **trước** khi gọi LLM; LLM lỗi → thêm dòng trợ lý `status='error'` + `error_code`, API trả mã ổn định (429 `llm_rate_limited`/`llm_quota_exhausted` kèm `Retry-After` nếu có, 504 `llm_timeout`, 502 `llm_provider_error`/`llm_invalid_response`, 422 `llm_content_blocked`, 503 `llm_not_configured`). API không trả model/token cho frontend; DB lưu `model_id`, `input_tokens`, `output_tokens`, `latency_ms`, `truncated`.
- Migration `694e39a25fe6` (autogenerate so với **DB test**): `chat_sessions`, `chat_messages` + index `(user_id, updated_at DESC)`, `(session_id, created_at)`; CHECK `role`, `status`, `status='ok' OR error_code IS NOT NULL`; FK `RESTRICT`. Trên DB test: upgrade → `alembic check` không lệch → downgrade -1 (còn `alembic_version, learner_profiles, users`) → upgrade lại → `check` không lệch. **DB chính chưa migrate** (vẫn `58871d077b8e`), chờ người dùng cho phép.
- Test mới: `test_chat_history.py` (9), `test_prompts.py` (7), `test_chat_api.py` (28). Làm hỏng code có chủ đích (khôi phục, `cmp` xác nhận): bỏ kiểm tra chủ sở hữu phiên → 1 failed; LLM lỗi thì xóa tin người dùng → 7 failed; không cắt lịch sử theo N → 1 failed; gửi lại lượt lỗi cho LLM → 3 failed; ghép nội dung người dùng vào system prompt → 1 failed; ghi nội dung tin nhắn vào log → 1 failed.
- `pytest` không mạng, không key (`GEMINI_API_KEY=""`, `LLM_PROVIDER=fake`, proxy cổng chết): **215 passed, 1 skipped**; chạy bình thường: 215 passed, 1 skipped, không cảnh báo. DB test sau khi chạy: 0 user, 0 phiên, 0 tin nhắn.
- Quét secret: `GEMINI_API_KEY`, `POSTGRES_PASSWORD`, `JWT_SECRET` không có trong file sẽ commit hay lịch sử Git.

### Chưa kiểm chứng

- Chat với Gemini thật qua API (chưa gọi; DB chính chưa migrate nên endpoint chat chưa chạy được trên DB chính).
- Chất lượng thật của prompt gia sư (đúng ngôn ngữ, theo trình độ, quy tắc a/an theo âm) với model thật.
- Cột `truncated` là bổ sung ngoài danh sách thay đổi ERD đã duyệt (phát sinh từ yêu cầu cờ cắt cụt ở Buổi 2) — cần người dùng xác nhận.
- Giới hạn tần suất, prompt injection nâng cao: Buổi 4.

### Buổi 3 — sau khi người dùng duyệt (2026-11-23)

Người dùng cho phép: migrate DB chính, duyệt cột `truncated`, chat thật 1 lần, commit/push.

- **DB chính:** trước `users/learner_profiles = 1/1`; `alembic upgrade head` → `Running upgrade 58871d077b8e -> 694e39a25fe6`; `alembic current` → `694e39a25fe6 (head)`; `alembic check` → không lệch; sau `1/1` (dữ liệu nguyên vẹn). Bảng: `alembic_version, chat_messages, chat_sessions, learner_profiles, users`.
- `docs/DATABASE_DESIGN.md`: ghi các bổ sung đã duyệt cho `chat_sessions` (`title`) và `chat_messages` (`status`, `error_code`, `model_id`, `input_tokens`, `output_tokens`, `latency_ms`, `truncated`).
- **Chat thật 1 lần qua toàn bộ API** (đăng ký → đăng nhập → tạo phiên → gửi tin → đọc lại), trên DB test trong một transaction rồi rollback (DB test sau đó 0 user, 0 tin nhắn); ép `LLM_MAX_RETRIES=0`, không model dự phòng. Câu hỏi: "Khi nào dùng 'a' và khi nào dùng 'an'? Cho ví dụ với 'hour' và 'university'." Kết quả: HTTP 200, model thực tế `gemini-3.5-flash-lite`, **3072 ms**, token vào/ra **393/295**, `truncated=False`; lịch sử đọc lại `[user ok, assistant ok]`. Key không xuất hiện trong output.
- Nhận xét nội dung (Claude đánh giá): giải thích bằng tiếng Việt, ví dụ tiếng Anh có dịch — đúng yêu cầu. Quy tắc a/an **đúng theo âm** (*an hour*: h câm; *a university*: âm /ju:/) — đã khắc phục lỗi của hai lần gọi trước. Chưa chuẩn: câu tóm tắt vẫn liệt kê "u, e, o, a, i" như chữ cái; đưa 4 ví dụ trong khi prompt yêu cầu tối đa 3.
