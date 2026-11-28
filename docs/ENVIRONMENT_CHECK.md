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

## Tuần 3 — hoàn thiện Buổi 2–3 (2026-11-23)

### Claude đã chạy

- **Không giữ kết nối DB khi chờ LLM** (`services/chat.py::send_message`): đọc trước `session_id`, `language_code`, lịch sử, trình độ, system prompt vào biến cục bộ; commit tin người dùng rồi gọi LLM **không** `refresh` (trước đây `db.refresh(user_row)` mở transaction mới và giữ kết nối suốt thời gian chờ LLM); chỉ `refresh` sau khi đã có trả lời. Test: `session.in_transaction()` lúc FakeLLM chạy = `False`; với `Session` thật (không savepoint), `engine.pool.checkedout()` lúc FakeLLM chạy = `0`.
- **Lỗi ngoài dự kiến:** lỗi không phải `LLMError` → lưu dòng trợ lý `status='error'`, `error_code='internal_error'`, log `chat internal_error session=... exc_type=...` (không nội dung), ném lại; thêm bộ xử lý lỗi chung trả `500 {"error": {"code": "internal_error", ...}}` (log chỉ tên lớp lỗi). Lưu ý: provider ném `RuntimeError` được `LLMService` chuẩn hóa thành `llm_invalid_response` (502) từ Buổi 1 — có test riêng; nhánh `internal_error` được kiểm bằng lớp LLM bị lỗi lập trình.
- **list_messages:** lấy `limit` tin mới nhất rồi đảo lại thứ tự tăng dần (test với `limit=3` trên phiên 8 tin).
- `.env.example` + README: `CHAT_HISTORY_TURNS=10`, `CHAT_MAX_MESSAGE_CHARS=2000` kèm chú thích.
- `prompts/en/tutor.md`: thêm quy tắc "Never give more than three examples ... this limit is strict" và "summarize the a/an rule only in terms of sounds ... Do not list letters". `test_prompts.py` kiểm tra hai câu này. **Không gọi API thật để thử.**
- `docs/PROMPT_WEEK3.md` (Buổi 6): thêm mục hiển thị `truncated` và thông báo nội dung chat gửi tới Google (gói miễn phí có người đọc).
- Test mới `test_chat_robustness.py` (6). Làm hỏng code có chủ đích (khôi phục, `cmp` xác nhận): `refresh` tin người dùng trước khi gọi LLM → 2 failed (cả `in_transaction` lẫn `pool.checkedout`); bỏ nhánh bắt lỗi ngoài dự kiến → 1 failed; `list_messages` lấy tin cũ nhất → 1 failed; bỏ bộ xử lý lỗi 500 chung → 1 failed.
- `pytest` không mạng, không key (`GEMINI_API_KEY=""`, `LLM_PROVIDER=fake`, proxy cổng chết): **222 passed, 1 skipped**; chạy bình thường: 222 passed, 1 skipped, không cảnh báo. `alembic check`: DB test và DB chính đều không lệch (không đổi schema). DB test sau khi chạy: 0 user, 0 tin nhắn.
- Quét secret (thư mục làm việc + 12 commit): `GEMINI_API_KEY`, `POSTGRES_PASSWORD`, `JWT_SECRET` không có; `.env.example` không có giá trị key.

### Chưa kiểm chứng

- Hiệu quả thật của hai quy tắc prompt mới (giới hạn 3 ví dụ, tóm tắt a/an chỉ theo âm) với Gemini — chưa gọi API.
- Hành vi giữ kết nối dưới tải đồng thời nhiều request (mới kiểm chứng một request).

## Tuần 3 — Buổi 4: giới hạn tần suất, chống lạm dụng, an toàn chat (2026-11-23)

### Claude đã chạy

- **Không cài thư viện mới.** `tzdata` 2026.6 đã có sẵn (do `psycopg` kéo theo trên Windows); vì code dùng trực tiếp `zoneinfo` cho `USER_TIMEZONE` nên ghim `tzdata==2026.6` vào `requirements.txt`. `pip check`: không lỗi. Kiểm tra: 17:00:00Z → `2026-11-24 00:00:00+07:00` (Asia/Ho_Chi_Minh).
- **LLMService với lỗi hết hạn mức NGÀY** (đọc code, không đoán): `LLMQuotaExhaustedError.retryable = False` → `service.py` dòng 87–88 thoát vòng thử lại ngay, không gọi lại cùng model; `fallback_allowed = True` → chuyển sang model dự phòng. Đã có test `test_non_transient_errors_are_not_retried` (max_retries=3 vẫn 1 lần gọi). **Không cần sửa.**
- Tạo `app/core/rate_limit.py` (cửa sổ trượt dạng nhật ký, `ConcurrencyGuard`, `Cooldown`; `threading.Lock`; đồng hồ thay được; ≤ 10.000 khóa, dọn khóa hết hạn rồi bỏ khóa cũ nhất), `app/core/limits.py` (`AppLimits` gắn vào `app.state`, `client_ip` không tin `X-Forwarded-For` khi `TRUSTED_PROXY_COUNT=0`, `mask_ip`, ranh giới ngày theo múi giờ, log từ chối chỉ metadata). Cấu hình mới trong `config.py` (có `ge/le`; `0` = tắt): `CHAT_USER_PER_MINUTE=6`, `CHAT_USER_PER_DAY=40`, `CHAT_MAX_CONCURRENT_PER_USER=1`, `LLM_GLOBAL_PER_MINUTE=10`, `LLM_GLOBAL_PER_DAY=0`, `AUTH_LOGIN_FAILS_PER_EMAIL=5`, `AUTH_LOGIN_FAILS_PER_IP=20`, `AUTH_LOGIN_WINDOW_SECONDS=900`, `AUTH_REGISTER_PER_IP_PER_HOUR=10`, `USER_TIMEZONE=Asia/Ho_Chi_Minh`, `TRUSTED_PROXY_COUNT=0`. `.env.example`, README cập nhật; **`.env` không sửa** (dùng mặc định).
- Đăng nhập: chặn theo email chuẩn hóa và IP → `429 auth_rate_limited` + Retry-After; đăng nhập đúng xóa bộ đếm email; giữ nguyên băm giả khi email không tồn tại. Đăng ký: giới hạn theo IP mỗi giờ.
- Chat: thứ tự 404 → 422 → `409 chat_busy` → `429 chat_rate_limited` / `429 chat_daily_limit_reached` → `429 service_busy` → lưu → LLM; khóa đang xử lý nhả trong `finally`; lỗi `llm_rate_limited`/`llm_quota_exhausted` thật → tạm khóa toàn hệ thống theo `retry_after` (mặc định 30s, tối đa 60s). Giới hạn ngày đếm tin người dùng hôm nay trừ lượt hỏng do hệ thống/nhà cung cấp (giữ quyết định Tuần 3 mục 5); lượt bị chặn vì nội dung vẫn tính.
- Đầu vào chat: bỏ ký tự điều khiển/NUL (giữ `\n`, `\t`), chuẩn hóa xuống dòng, tối đa 100 dòng. Không lọc từ khóa; 3 test cấu trúc với tin nhắn tấn công (in system prompt, thẻ `</system>` giả, đổi vai).
- Test mới: `test_rate_limit.py` (12), `test_auth_limits.py` (17), `test_chat_limits.py` (24, gồm 1 test đồng thời thật: 5 luồng, 5 session DB riêng → đúng 1 `ok`, 4 `chat_busy`). Ranh giới nửa đêm: tin lúc 23:59:59 giờ VN không tính, tin lúc 00:00:00 giờ VN tính; Retry-After = 86370s khi "bây giờ" là 00:00:30.
- **Làm hỏng code có chủ đích** (script áp dụng từng thay đổi, chạy `test_rate_limit/test_auth_limits/test_chat_limits/test_auth`, khôi phục; so sánh byte toàn bộ `backend/app` xác nhận nguyên vẹn):

| Làm hỏng | Kết quả |
| --- | --- |
| Bỏ Lock (mọi bộ giới hạn) | 2 failed |
| Không nhả khóa đồng thời khi lỗi | 9 failed |
| Kiểm giới hạn SAU khi lưu tin | 3 failed |
| Route không chuẩn hóa email | 0 failed — schema `LoginRequest` đã chuẩn hóa trước (lớp bảo vệ thật) |
| Schema `LoginRequest` không chuẩn hóa email (kèm route) | 2 failed |
| Tính ngày theo UTC thay vì `USER_TIMEZONE` | 2 failed |
| Không dọn khóa cũ | 1 failed |
| Tin cậy `X-Forwarded-For` | 2 failed |

  Phát hiện khi làm hỏng: lần đầu "bỏ Lock" chỉ 1 failed — test của `ConcurrencyGuard` không bắt được vì `SlowDict` ngủ TRƯỚC khi đọc (các luồng đọc giá trị đã cập nhật). Sửa test: đọc rồi mới ngủ. Sau sửa: có Lock 3/3 lần pass, bỏ Lock 3/3 lần đỏ cả 2 test.
- `pytest` không mạng, không key (`GEMINI_API_KEY=""`, `LLM_PROVIDER=fake`, proxy cổng chết): **275 passed, 1 skipped** (smoke), không cảnh báo. Chạy bình thường 3 lần liên tiếp: 275 passed, 1 skipped mỗi lần (test đồng thời ổn định). Thời gian 35–65s (test chậm nhất 1,4s do đăng ký/đăng nhập nhiều tài khoản với Argon2; không có ngủ thật).
- `alembic check`: DB test và DB chính không lệch (không đổi schema). DB test sau khi chạy: 0 user, 0 tin nhắn.
- Quét secret (thư mục làm việc + 12 commit): `GEMINI_API_KEY`, `POSTGRES_PASSWORD`, `JWT_SECRET` không có; `.env.example` không có giá trị key.

### Chưa kiểm chứng

- **Hành vi dưới tải thật nhiều tiến trình** (nhiều worker uvicorn/gunicorn, nhiều máy): bộ đếm trong bộ nhớ chỉ đúng với một tiến trình; chưa thử tải thật.
- **Giá trị RPD thật** của gói miễn phí: chưa biết → `LLM_GLOBAL_PER_DAY=0` (tắt). Người dùng cần đặt sau khi xem AI Studio.
- Tạm khóa sau 429 mới kiểm chứng bằng FakeLLM; chưa gặp 429 thật từ Google.
- Hiệu quả chống prompt injection với model thật (FakeLLM chỉ chứng minh cấu trúc) — Tuần 7.
- **Người dùng tự báo (2026-11-23):** RPD gói miễn phí của `gemini-3.5-flash-lite` = **500** (từ AI Studio). Khuyến nghị `LLM_GLOBAL_PER_DAY=200` (500 × 0,8 ÷ 2); người dùng tự đặt trong `.env` — Claude không sửa `.env` và chưa kiểm chứng giá trị đã đặt.
- **Claude đã chạy (2026-11-23):** đọc lại `.env` sau khi người dùng đặt (không in key): `LLM_GLOBAL_PER_DAY=200` có đúng 1 dòng, không khoảng trắng thừa, không dòng trùng; `Settings()` đọc được `200`; các ngưỡng khác giữ mặc định (`LLM_GLOBAL_PER_MINUTE=10`, `CHAT_USER_PER_MINUTE=6`, `CHAT_USER_PER_DAY=40`, `LLM_MAX_RETRIES=1`, `USER_TIMEZONE=Asia/Ho_Chi_Minh`); `GEMINI_API_KEY` vẫn còn.
- **Người dùng chốt (2026-11-23):** giữ ngưỡng mặc định Buổi 4; giữ cách đếm giới hạn ngày trừ lượt hỏng do hệ thống/nhà cung cấp. Khuyến nghị tối ưu gói miễn phí (giới hạn thực tế là RPD 500, không phải TPM): đặt `LLM_PROVIDER=fake` khi phát triển giao diện (Buổi 6), không thử chat trên `/docs` khi đang dùng `gemini`, chạy smoke test thật hạn chế, giữ `LLM_MAX_OUTPUT_TOKENS=1024` (trả lời thật ~300 token; giảm không tiết kiệm lượt gọi mà tăng nguy cơ cắt cụt).

### Buổi 4 — hoàn thiện: chế độ `fake` không tính hạn mức (2026-11-23)

Người dùng đồng ý (phương án 3) và cho phép commit/push.

- **Claude đã chạy:** thêm `LLMProvider.consumes_quota` (mặc định `True`; `FakeLLM` mặc định `False`, test giả lập nhà cung cấp thật đặt `True`) và `LLMService.consumes_quota`. Khi nhà cung cấp không tốn hạn mức: câu trả lời lưu `model_id = "fake:<model>"` (lỗi: `"fake:"`) — cần thiết vì `.env` hiện đặt `LLM_PROVIDER=fake` kèm `LLM_MODEL_ID=gemini-3.5-flash-lite`, nếu không đánh dấu thì không phân biệt được trong DB; giới hạn ngày mỗi người và toàn hệ thống trừ lượt `fake:`; bỏ qua ngưỡng phút toàn hệ thống và tạm khóa. Vẫn giữ giới hạn phút mỗi người và khóa đồng thời. Test mới `test_chat_fake_mode.py` (7): đánh dấu `fake:` kể cả khi model ID trông như thật; lượt thật không bị đánh dấu; 4 tin `fake` liên tiếp với ngưỡng ngày/toàn hệ thống = 1 đều 200; bỏ qua tạm khóa; vẫn chặn theo phút và `chat_busy`; sau khi chuyển sang gọi thật, lượt `fake` trước đó không bị tính. Làm hỏng có chủ đích (khôi phục, `cmp` xác nhận): không đánh dấu `fake:` → 5 failed; áp giới hạn toàn hệ thống cho `fake` → 2 failed; đếm lượt `fake` vào giới hạn ngày → 3 failed. `.env.example`, README, `ARCHITECTURE.md` cập nhật.

### Buổi 4 — hoàn thiện nhỏ (2026-11-23)

#### Claude đã chạy

- `docs/ARCHITECTURE.md` — bảng "Giới hạn đã biết": thêm (a) kẻ khác cố ý đăng nhập sai `AUTH_LOGIN_FAILS_PER_EMAIL` lần để khóa email người khác trong `AUTH_LOGIN_WINDOW_SECONDS` (chấp nhận cho đồ án; Tuần 8: khóa theo cặp email + IP hoặc CAPTCHA); (b) tạm khóa sau hết hạn mức ngày nằm trong bộ nhớ, mất khi khởi động lại. Ghi rõ `LLM_GLOBAL_PER_MINUTE` đếm request người dùng, không đếm lời gọi thật (tối đa (1 + `LLM_MAX_RETRIES`) × số model lời gọi mỗi request), khuyến nghị điểm xuất phát `15 ÷ (1 + LLM_MAX_RETRIES)` (= 7 với `LLM_MAX_RETRIES=1`); không đổi code ở mục này.
- Cấu hình `LLM_QUOTA_COOLDOWN_SECONDS` (mặc định 900; 0 hoặc 60–3600, giá trị 1–59 bị từ chối). Hàm thuần `llm_cooldown_seconds()`: `llm_rate_limited` giữ nguyên (retry_after, mặc định 30s, tối đa 60s); `llm_quota_exhausted` khóa theo cấu hình (0 = như theo phút). Trần cứng của bộ tạm khóa nâng từ 60 lên 3600 giây. `.env.example`, README, `ARCHITECTURE.md` cập nhật; `.env` không sửa (app dùng mặc định 900).
- Test mới/sửa (`test_chat_limits.py`): quota_exhausted khóa 900s còn rate_limited 20s; còn 1 giây vẫn `service_busy`, hết hạn thì 200; cấu hình 0 → 60s; 9 trường hợp hàm thuần; kiểm tra khoảng cấu hình. Làm hỏng có chủ đích (khôi phục, `cmp` xác nhận): hết hạn mức ngày khóa ngắn → 5 failed; rate_limited khóa lâu → 7 failed; quên nâng trần cứng (vẫn 60s) → 3 failed; bỏ kiểm tra khoảng 60–3600 → 2 failed.
- `pytest` không mạng, không key: **303 passed, 1 skipped**; chạy bình thường: 303 passed, 1 skipped, không cảnh báo. `alembic check`: DB test và DB chính không lệch. Quét secret: sạch.

#### Chưa kiểm chứng

- Chưa gặp `llm_quota_exhausted` thật từ Google: cấu trúc lỗi hết hạn mức ngày (QuotaFailure PerDay) mới kiểm bằng test.
- Mức `LLM_GLOBAL_PER_MINUTE` tối ưu dưới tải thật (khuyến nghị 7, đang để 10).

## Tuần 3 — Buổi 5: placement test (backend) (2026-11-23)

Người dùng: giữ `LLM_GLOBAL_PER_MINUTE=10`. Phần hoàn thiện nhỏ Buổi 4 chưa được cho phép commit → gộp vào lần commit sau.

### Claude đã chạy

- **Chấm điểm** (`services/placement_scoring.py`, hàm thuần, không LLM): trình độ cao nhất có ngưỡng ≤ điểm, so sánh nguyên (`đúng × 100 ≥ ngưỡng × tổng`); nhóm (trình độ × loại) yếu khi < 60%; chủ đề làm sai; câu lạ → `unknown_question`, lựa chọn lạ → `invalid_option`. Không chứa mã trình độ cố định (có test). `LanguageConfig.placement` đọc và kiểm tra chặt khối `placement` của YAML (percent, đúng quy tắc, trình độ thấp nhất = 0, tăng dần ≤ 100); `en.yaml` thêm `question_set: placement_v1`.
- **Migration `dfd85f565969`** (autogenerate so với DB test): `questions` (`external_id` UNIQUE, `question_set`, `category`; chưa có `source_document_id`), `placement_results` (`status`, `question_ids`, `started_at`, `applied_at`; CHECK kết quả đầy đủ khi `completed`; unique index có điều kiện một lượt `in_progress` mỗi người/ngôn ngữ). DB test: upgrade → check sạch → downgrade -1 → upgrade → check sạch. Phát hiện khi tự soát: `started_at` mặc định `now()` (thời điểm bắt đầu transaction) → đổi sang `clock_timestamp()` cho `started_at`, `completed_at`, `applied_at`; chạy lại downgrade/upgrade trên DB test, `column_default = clock_timestamp()`. **DB chính chưa migrate** (`694e39a25fe6`; `alembic check` báo "not up to date" đúng dự kiến).
- **Nạp câu hỏi** (`services/question_bank.py` + `scripts/load_placement.py --target test|main [--dry-run]`): kiểm tra bằng validator Tuần 1 trước, idempotent theo `external_id`, chỉ đọc file nguồn (SHA-256 trước/sau bằng nhau trong test). Dry-run trên DB test: `30 câu — thêm 30, cập nhật 0, không đổi 0 — DRY-RUN (không ghi)`. **Chưa nạp vào DB nào** (test tự nạp trong transaction rồi rollback).
- **API** `/api/v1/placement/attempts`: bắt đầu (201; đang có lượt dở → 200 trả lại lượt đó), danh sách, chi tiết, nộp (`SELECT ... FOR UPDATE`; lần hai → 409 `placement_already_submitted`), `apply` (xác nhận mới cập nhật `current_level_code`, ghi `applied_at`, gọi lại không lỗi). Lượt người khác → 404 `placement_not_found`; ngôn ngữ không hỗ trợ/chưa nạp câu hỏi → 422 `placement_not_available`. `answer_summary` lưu chi tiết từng câu (chốt câu hỏi còn mở trong ERD).
- Test mới: `test_placement_scoring.py` (25), `test_placement_api.py` (26, dùng bộ câu hỏi THẬT). Điểm kỳ vọng tính tay: 30/21/20/12/11/0 câu đúng → B1/B1/A2/A2/A1/A1; sai 3/5 ngữ pháp A2 → nhóm yếu duy nhất (2/5 = 40%), 3/5 = 60% không yếu. Phản hồi khi đang làm bài được duyệt đệ quy: không có khóa `correct_answer`, `explanation`, `is_correct`, `level_code`, `topic`, `answer_summary` (cả schema OpenAPI). Nộp đồng thời thật (2 luồng, chấm điểm làm chậm 0,3s): đúng 1 `ok`, 1 `placement_already_submitted`.
- **Làm hỏng code có chủ đích** (khôi phục, so sánh byte toàn bộ `backend/app`): lộ đáp án → 2 failed; ngưỡng `>` thay `>=` → 5; bỏ `FOR UPDATE` → 1; bỏ kiểm tra chủ sở hữu → 1; tự cập nhật trình độ khi nộp → 13; nhóm yếu `<=` → 1; bỏ kiểm tra câu lạ → 2. **Sự cố trong lần chạy đầu:** lần làm hỏng thứ 4 làm bộ test treo quá 600s; script ngắt, khôi phục code và kết thúc exit 0 mà chưa chạy các lần 4–7. Nguyên nhân khả dĩ: hai test đồng thời dùng luồng non-daemon, `barrier.wait()` không giới hạn và `FOR UPDATE` có thể chờ vô hạn. Đã gia cố: luồng daemon, `barrier.wait(timeout=15)`, `lock_timeout=15000` cho session test, ghi nhận mọi exception. Chạy lại đủ 7 lần với giới hạn 240s mỗi lần: **0 lần timeout**, cả 7 đều bị bắt.
- `pytest` không mạng, không key: **354 passed, 1 skipped**; chạy bình thường: 354 passed, 1 skipped, không cảnh báo. Hai script validate: 0 lỗi. DB test sau khi chạy: 0 user, 0 câu hỏi, 0 lượt placement. Quét secret: sạch.

### Chưa kiểm chứng

- Migration và nạp câu hỏi trên **DB chính** (chờ người dùng cho phép).
- Độ tin cậy của 30 câu và ngưỡng 40%/70% với người học thật (ngưỡng tạm thời; hiệu chuẩn ở Tuần 7).
- Nguyên nhân chính xác của lần treo đầu (không tái hiện được khi chạy riêng; đã loại bỏ các điểm có thể chờ vô hạn).

### Buổi 5 — migration và nạp câu hỏi vào DB chính (2026-11-23/24)

Người dùng cho phép: migrate DB chính, nạp 30 câu hỏi vào DB chính.

#### Claude đã chạy

- **Migration DB chính:** trước `users/learner_profiles/chat_sessions/chat_messages = 1/1/0/0`; `alembic upgrade head` → `Running upgrade 694e39a25fe6 -> dfd85f565969`; `alembic current` → `dfd85f565969 (head)`; `alembic check` → không lệch; sau `1/1/0/0`. Có `questions`, `placement_results`, index `uq_placement_results_one_in_progress`, `started_at` mặc định `clock_timestamp()`.
- **Nạp câu hỏi lần đầu thất bại an toàn:** Docker Desktop lại tắt (máy khởi động lại) → cả 3 lệnh lỗi kết nối, không ghi gì, file nguồn không đổi. Cải tiến `scripts/load_placement.py`: lỗi kết nối → một dòng `ERROR: không kết nối được DB (...). Thử: docker compose up -d --wait` (exit 2) thay vì traceback; thiếu bảng → nhắc chạy migration. Claude mở lại Docker Desktop; DB chính còn nguyên (1 user, 0 câu hỏi, `dfd85f565969`).
- **Nạp vào DB chính:** dry-run `thêm 30 … DRY-RUN (không ghi)` (vẫn 0 câu); nạp thật `thêm 30 … đã ghi` (30 câu); chạy lại `thêm 0, cập nhật 0, không đổi 30` (vẫn 30 — idempotent). Phân bố: mỗi trình độ A1/A2/B1 có 5 ngữ pháp + 5 từ vựng; 30 `external_id` khác nhau; 30/30 đáp án đúng nằm trong danh sách lựa chọn. File nguồn không đổi (SHA-256 trước/sau bằng nhau).
- **Kiểm tra toàn luồng trên DB chính** (transaction rồi rollback, không LLM): đăng ký → bắt đầu 201, 30 câu, không lộ đáp án → nộp 15/30 đúng → đề xuất A2 "Sơ trung cấp", 3 nhóm yếu → nộp lại `placement_already_submitted` → xác nhận → hồ sơ A2. Sau rollback: DB chính 1 user, 0 lượt placement, 30 câu hỏi.
- `pytest` không mạng, không key: **354 passed, 1 skipped**; `alembic check` DB chính và DB test: không lệch.

### Buổi 5 — hoàn thiện (2026-11-24)

#### Claude đã chạy

- **Lượt đang làm lỗi thời** (`services/placement.py`): `start_attempt` kiểm tra `question_ids` của lượt dở còn đủ trong `questions`; nếu thiếu → `DELETE` lượt đó với điều kiện `result_id` + `user_id` + `status='in_progress'` ngay trong câu lệnh (không bao giờ xóa lượt đã nộp), log `placement stale_attempt_discarded attempt=... deleted=...`, tạo lượt mới từ bộ câu hỏi hiện tại → 201. `get_attempt` với lượt dở lỗi thời vẫn trả 409 `placement_questions_changed`. Không đổi schema, không migration.
- **apply chỉ với lượt mới nhất:** so với lượt `completed` mới nhất (theo `completed_at`, rồi `started_at`) của người dùng cho cùng ngôn ngữ; lượt cũ hơn → 409 `placement_superseded` ("Đã có kết quả mới hơn"); gọi lại với lượt mới nhất không lỗi; lượt mới đang làm (chưa nộp) không chặn việc áp dụng lượt đã nộp.
- Test mới `test_placement_lifecycle.py` (6): xóa một câu trong transaction test → xem lượt dở cũ 409 → `start` trả 201 với 29 câu, lượt dở cũ đã bị xóa, lượt đã nộp của chính người dùng và của người khác còn nguyên, log có `stale_attempt_discarded`; gọi nhầm hàm xóa với lượt đã nộp → không xóa; apply lượt cũ → 409 và `applied_at` vẫn NULL; apply lượt mới nhất hai lần → 200 cả hai.
- Làm hỏng có chủ đích (khôi phục, `cmp` xác nhận): không xóa lượt dở lỗi thời → 1 failed; xóa nhầm cả lượt đã nộp (bỏ điều kiện `status` và `result_id`) → 2 failed; bỏ kiểm tra lượt mới nhất khi apply → 1 failed; lấy lượt cũ nhất thay vì mới nhất → 2 failed.
- Tài liệu: `ARCHITECTURE.md` — mục placement và bảng "Giới hạn đã biết" (làm lại với cùng 30 câu sau khi xem đáp án; trình độ chỉ theo điểm tổng, ngưỡng tạm thời, hiệu chuẩn Tuần 7; endpoint placement chưa giới hạn tần suất vì không dùng LLM; câu hỏi bị xóa làm lượt đã nộp không xem lại chi tiết được). `PROMPT_WEEK3.md` checklist Buổi 6: xử lý `placement_superseded`, `placement_questions_changed`.
- `pytest` không mạng, không key: **360 passed, 1 skipped**; chạy bình thường: 360 passed, 1 skipped, không cảnh báo. `alembic check` DB test và DB chính: không lệch. DB test sau khi chạy 0/0/0 (user/câu hỏi/lượt); DB chính 1 user, 30 câu hỏi, 0 lượt (không đổi). Quét secret: sạch.

#### Chưa kiểm chứng

- Lượt đã nộp dùng câu hỏi bị xóa không xem lại chi tiết được (409) — mới ghi thành giới hạn, chưa xử lý (cách tránh: không xóa câu đã dùng, tạo `question_set` mới).
- Hai request `start` đồng thời đúng lúc lượt dở bị lỗi thời: unique index chặn trùng, request thua nhận lại lượt mới; chưa có test đồng thời riêng cho trường hợp này.

## Tuần 3 — Buổi 6: giao diện chat và placement (2026-11-24)

### Claude đã chạy

- **Lỗi backend thật phát hiện trước khi viết giao diện:** phản hồi 429 có `Retry-After` nhưng CORS không có `Access-Control-Expose-Headers` → JavaScript khác origin (5173 → 8000) không đọc được → đếm ngược không có số giây. Người dùng cho phép sửa: thêm `expose_headers=["Retry-After"]` vào `CORSMiddleware` (`backend/app/main.py`) + test `test_retry_after_is_exposed_to_browser_on_rate_limited_response` (dùng hết lượt trong bộ đếm để request bị chặn TRƯỚC khi chạm DB). Làm hỏng có chủ đích (`expose_headers=[]`) → 1 failed; khôi phục, `cmp` xác nhận.
- **Sự cố do Claude gây ra và đã khắc phục:** lần kiểm tra CORS đầu tiên dùng `create_app()` không đổi DB → lần đăng ký đầu tiên ghi tài khoản `cors-a@example.com` vào **DB chính**. Claude kiểm tra (0 phiên chat, 0 lượt placement) rồi xóa đúng hồ sơ + tài khoản đó trong một transaction có điều kiện email; DB chính trở về 1 user, 1 hồ sơ. Test viết sau đó cũng được sửa để không chạm DB. Mọi kiểm tra HTTP còn lại chạy trên DB test.
- **Frontend (không thêm thư viện):** `types.ts` (kiểu chat/placement khớp `backend/app/schemas/chat.py`, `placement.py`), `api/client.ts` (thêm hàm chat/placement, `ApiRequestError.retryAfterSeconds`), `lib/{apiErrors,time,chat,placement}.ts` (logic thuần), `hooks/useCountdown.ts`, `components/ProtectedRoute.tsx`, `pages/{ChatPage,PlacementPage}.tsx`, route `/chat`, `/placement`, liên kết trong `AppLayout` (màn hình hẹp chỉ biểu tượng + `aria-label`), đếm ngược `auth_rate_limited` ở Login/Register, CSS `:focus-visible`, `button:disabled { cursor: not-allowed }`, `.secondary-button`.
- **Logic thuần kiểm bằng Node 24 + `node:assert`** (chạy trực tiếp file `.ts`, không thêm framework): 12 nhóm đạt. Kiểm tra bắt được lỗi thật: `parseRetryAfter("-5")` trả 0 vì `Date.parse` hiểu là năm -5 → chỉ nhận ngày HTTP dạng IMF-fixdate.
- `npm run build` (`tsc -b` + `vite build`): pass, 1710 modules; lần đầu báo 1 lỗi `noUnusedParameters` (đã sửa); không cảnh báo TypeScript còn lại.
- **Luồng HTTP thật** (uvicorn cổng 8010, `POSTGRES_DB=ai_language_tutor_test`, `LLM_PROVIDER=fake`, `GEMINI_API_KEY=""`, header `Origin: http://localhost:5173`): đăng ký 201 → tạo phiên 201 → gửi tin 200 (FakeLLM, phản hồi không có `model_id`/token) → lịch sử `[user ok, assistant ok]` → tiêu đề phiên = tin đầu → tin 2001 ký tự `422 message_too_long` "Tin nhắn dài tối đa 2000 ký tự." → tin thứ 7 trong 1 phút `429 chat_rate_limited`, `Retry-After: 60`, `Access-Control-Expose-Headers: Retry-After`, `Access-Control-Allow-Origin: http://localhost:5173`. Placement: bắt đầu 201, 30 câu, không có khóa `correct_answer/explanation/is_correct/level_code/topic` → bắt đầu lại 200 cùng lượt → nộp 20/30 câu (chọn bừa) → 5/30 (16,7%) A1 "Sơ cấp", review 30 câu, có `disclaimer` → nộp lại `placement_already_submitted` → apply lượt cũ `409 placement_superseded` → apply lượt mới nhất 200. Đăng nhập sai lần 6 → `429 auth_rate_limited`, `Retry-After: 900`, expose đúng. Log server không chứa nội dung tin nhắn. Dọn DB test sau đó: 0 user, 0 câu hỏi, 0 tin nhắn; DB chính không đổi (1 user, 30 câu hỏi).
  - Lần chạy đầu in `Retry-After=None`: lỗi của **script kiểm tra** (chuyển header sang `dict` rồi tra chữ hoa trong khi uvicorn gửi chữ thường), không phải backend; sửa script và chạy lại cho kết quả trên.
- Vite dev: `/chat`, `/placement` → 200 (SPA). Quét `src`: không `dangerouslySetInnerHTML`, `innerHTML`, `console.log`; `localStorage` chỉ trong chú thích; `sessionStorage` chỉ cho token; `correct_answer` chỉ ở phần xem lại sau khi nộp.
- `pytest` không mạng, không key: **361 passed, 1 skipped**. `alembic check` DB test và DB chính: không lệch. Quét secret (thư mục làm việc, 13 commit, `frontend/dist`): sạch.

### Người dùng tự báo

- (Chưa có — chờ người dùng thử trên trình duyệt theo danh sách trong báo cáo Buổi 6.)

### Chưa kiểm chứng trên trình duyệt

Toàn bộ thao tác trên giao diện (bấm, gõ, đếm ngược hiển thị, bố cục màn hình hẹp 360px, focus bằng bàn phím, Enter khi gõ Telex/VNI) — Claude không quan sát được trình duyệt; chỉ kiểm chứng qua build TypeScript và các phản hồi HTTP mà giao diện sẽ nhận.

## Tuần 3 — Buổi 6 — hoàn thiện (2026-11-25)

Không sửa backend, không sửa `.env`, không gọi API thật, không chạm DB chính, không thêm thư viện, không commit.

### Claude đã chạy

- **Đổi phiên trong lúc đang gửi** (`ChatPage.tsx`):
  - Nút "Cuộc trò chuyện mới" và các phiên khác bị khóa khi đang chờ trả lời. Có `title`, có dòng giải thích hiện trên màn hình, và `aria-describedby` trỏ tới dòng đó.
  - `selectedIdRef` được cập nhật đồng bộ qua `setSelectedId`.
  - `send()` chỉ ghi vào danh sách tin và tin đang chờ khi phiên của lượt gửi vẫn đang được chọn; nếu không thì chỉ làm mới danh sách phiên.
  - `loadMessages()` bỏ qua lịch sử của phiên khác về muộn.
  - Đếm ngược giới hạn vẫn bật dù đã đổi phiên, vì giới hạn tính cho cả tài khoản.
  - Điều kiện tách thành hàm thuần `isForCurrentSession` trong `src/lib/chat.ts`, có test.
- **Placement, lỗi `placement_questions_changed`:** `start(keepNotice)` đặt thông báo cùng lúc khởi tạo bài mới, nên thông báo không còn bị xóa. Các nút gọi `start` đổi thành `() => start()` để không truyền nhầm sự kiện click vào tham số. Hành vi khác không đổi.
- **Test logic lưu vào repo:**
  - 4 file `frontend/tests/*.test.ts` dùng `node:test` + `node:assert/strict`: 12 nhóm cũ cộng 1 nhóm mới `isForCurrentSession`.
  - Script `"test": "node --test tests/*.test.ts"`; không cần cờ thêm vì Node 24.15 tự bỏ kiểu TypeScript.
  - Cách ghi `node --test tests/` như trong yêu cầu **không chạy được**: Node 24 coi `tests/` là một file và báo `MODULE_NOT_FOUND`. Vì vậy script dùng glob, do Node tự mở rộng nên chạy giống nhau trong cả PowerShell lẫn bash.
- **`npm test`:** 13/13 pass, chạy được cả trong PowerShell và Git Bash, không có cảnh báo experimental.
- **Làm hỏng có chủ đích** (mỗi lần khôi phục xong đều xác nhận bằng `cmp`):

  | Hàm làm hỏng | Kết quả test |
  |---|---|
  | `parseRetryAfter`: bỏ kiểm tra định dạng IMF-fixdate | 1 fail |
  | `collapseRetriedTurns`: bỏ so nội dung | 1 fail |
  | `latestCompletedId`: đảo thứ tự sắp xếp | 2 fail |
  | `isForCurrentSession`: bỏ so phiên | 1 fail |
- **`npm run build`** (`tsc -b` + `vite build`): pass, không lỗi và không cảnh báo TypeScript.
- **Quét mã:** không có `dangerouslySetInnerHTML`, `innerHTML` hay `console.log/debug/info` trong `src` và `tests`.
- **`pytest`** không mạng, không key: **361 passed, 1 skipped** (không giảm).
- **Quét secret:** key Gemini, JWT secret và mật khẩu DB không có trong file sẽ commit, `frontend/dist`, hay lịch sử 14 commit.

### Người dùng tự báo

- Trước phần hoàn thiện này, ảnh chụp trang chat ở chế độ `fake` cho thấy: tin gửi và câu trả lời FakeLLM hiện đúng thứ tự, có 2 thông báo (không dẫn nguồn; dữ liệu gửi Google), bộ đếm `0/2000`.
- Các mục thử khác: chưa có báo cáo.

### Chưa kiểm chứng trên trình duyệt

- Nút phiên bị khóa trong lúc gửi: hiển thị, tooltip, trình đọc màn hình. Với FakeLLM lượt gửi xong rất nhanh, nên khó quan sát bằng mắt.
- Việc bỏ qua phản hồi hoặc lịch sử về muộn của phiên khác: chỉ kiểm qua hàm thuần và build. Chưa tái hiện được tình huống chạy đua thật trong trình duyệt.
- Thông báo "Bộ câu hỏi vừa được cập nhật…" khi gặp `placement_questions_changed`: muốn thấy phải đổi bộ câu hỏi trong DB, việc này chưa làm.
- File `tests/*.test.ts` không nằm trong `tsconfig` (`include: ["src"]`), nên `tsc` không kiểm kiểu cho chúng; Node chỉ bỏ kiểu chứ không kiểm.

## Tuần 3 — Buổi 7: kiểm thử toàn tuyến và nghiệm thu (2026-11-25)

Bảng tiêu chí nghiệm thu: `docs/WEEK3_ACCEPTANCE.md`. Không sửa `.env`, không migrate DB chính, không cài gì vào môi trường dự án, không commit.

### Claude đã chạy

**A. Kiểm tra tự động**

- `pytest` không mạng, không key (`GEMINI_API_KEY="" LLM_PROVIDER=fake HTTP(S)_PROXY=http://127.0.0.1:9`, `-rsw`): **370 passed, 1 skipped**, không có cảnh báo.
  - Mục skipped duy nhất là `test_llm_smoke.py` (gọi API thật, chỉ chạy khi `RUN_LLM_SMOKE=1`).
  - 370 = 361 test trước đó + 9 test mới trong `test_e2e_week3.py`.
- Frontend:
  - `npm test`: 13/13 pass.
  - `npm run build`: pass (`tsc -b` không lỗi).
- Alembic trên DB test (`alembic -x db=test …`):

  | Lệnh | Kết quả |
  |---|---|
  | `current` | `dfd85f565969 (head)` |
  | `upgrade head` | Không có gì để chạy |
  | `check` | "No new upgrade operations detected." |
  | `downgrade -1` | `dfd85f565969 -> 694e39a25fe6`, `current` = `694e39a25fe6` |
  | `upgrade head` | `694e39a25fe6 -> dfd85f565969` |
  | `check` | Không lệch |

  DB chính chỉ được đọc: `alembic current` = `dfd85f565969 (head)`, `alembic check` không lệch (lệnh chỉ so sánh, không ghi).
- Kiểm tra dữ liệu:
  - `scripts/validate_dataset.py`: "Validation passed: 15 records, 0 errors.", exit 0.
  - `scripts/validate_evaluation.py`: "30 placement questions, 30 RAG queries, 20 dev / 10 test", exit 0.
- Quét secret (lấy giá trị thật từ `.env`, chỉ đếm số lần xuất hiện, không in giá trị):
  - `GEMINI_API_KEY`, `JWT_SECRET`, `POSTGRES_PASSWORD`: 0 lần trong file sẽ commit, 0 trong `frontend/dist`, 0 trong `git log -p --all` (14 commit).
  - Chuỗi dạng `AIza…`: 0 ở cả ba nơi.
  - `.env` không được Git theo dõi và chưa từng được commit.
  - Trong `.env.example` cả ba biến đều trống.
- Log: đã đọc toàn bộ 13 lời gọi `logger.*` trong `backend/app`. Chỉ có metadata (đường dẫn, mã lỗi, id phiên/lượt, số ký tự, độ trễ, token, IP rút gọn); không lời gọi nào ghi nội dung tin, email hay mật khẩu.
  - Test đầu-cuối mới kiểm thêm bằng `caplog` ở mức DEBUG: nội dung câu hỏi và câu trả lời không xuất hiện trong log.

**B. Luồng đầu-cuối qua HTTP** (`backend/tests/test_e2e_week3.py`, 9 test)

Mỗi test dùng app riêng và transaction riêng, rollback sau khi chạy. LLM là FakeLLM; câu hỏi placement là bộ thật `placement_v1.json`.

1. Đăng ký → đăng nhập → tạo phiên → gửi 2 tin → lịch sử đúng thứ tự, đúng chủ.
   - Tiêu đề phiên lấy từ tin đầu.
   - System prompt chứa trình độ A1 của hồ sơ; lượt thứ hai gửi kèm lịch sử.
   - Phản hồi không có `model_id` hay token; log không chứa nội dung tin.
2. Người dùng B đọc, ghi, hoặc đoán phiên của A → 404 `chat_session_not_found`, giống hệt phiên không tồn tại. Không có tin nào được ghi thêm.
3. Giới hạn:
   - Tin thứ 7 trong phút → 429 `chat_rate_limited`, có `Retry-After` từ 1 đến 60 giây. Tin này không được lưu và LLM không bị gọi.
   - Đăng nhập sai 5 lần → lần thứ 6, kể cả đúng mật khẩu, nhận 429 `auth_rate_limited` kèm `Retry-After`.
4. Placement:
   - `start` → `get`: không có khóa đáp án nào trong câu hỏi.
   - Nộp 12/30 câu đúng → A2 (đúng ranh giới 40%), có review 30 câu và disclaimer.
   - Nộp lại → 409 `placement_already_submitted`.
   - Làm lượt thứ hai, đúng 30/30 → B1. Áp dụng lượt cũ → 409 `placement_superseded`, hồ sơ vẫn A1. Áp dụng lượt mới → hồ sơ B1, phiên chat mới mang trình độ B1.
   - Người dùng B không xem và không nộp được lượt của A → 404 `placement_not_found`.
5. Lỗi LLM giả lập (timeout, rate limit, content blocked):

   | Lỗi | HTTP | Mã lỗi |
   |---|---|---|
   | Timeout | 504 | `llm_timeout` |
   | Rate limit | 429 | `llm_rate_limited`, `Retry-After: 17` |
   | Content blocked | 422 | `llm_content_blocked` |

   - Thông điệp nội bộ cài sẵn (tên host, project, mã SAFETY, tên model) không lộ ra phản hồi.
   - Lượt lỗi được lưu `status='error'` với đúng `error_code`.
   - Lượt tiếp theo trả 200 và không gửi lại lượt lỗi cho LLM.

Làm hỏng có chủ đích (khôi phục xong đều xác nhận bằng `cmp`, `git status` sạch):

| Chỗ làm hỏng | Kết quả trên file e2e |
|---|---|
| Bỏ điều kiện `user_id` khi tìm phiên chat | 1 failed |
| Thêm `correct_answer` vào câu hỏi khi đang làm bài (schema + route) | 1 failed |
| Ngưỡng A2: 40 → 41 | 1 failed |
| Lưu lượt lỗi với `status="ok"` | 3 failed |

Lần thử đầu của mục thêm `correct_answer` **không áp dụng được**: mẫu chuỗi trùng 2 chỗ nên script từ chối. Vì vậy chỉ route bị sửa, Pydantic bỏ qua trường lạ và test vẫn xanh, đúng vì không có gì bị lộ. Chạy lại với mẫu chuỗi duy nhất thì test đỏ.

**C. Smoke test thật với Gemini** (người dùng cho phép 2 lời gọi; đã dùng đúng 2; mỗi ca không thử lại, không model dự phòng; key không xuất hiện trong output)

- Ca `text`: lời gọi **thành công**: model thực tế `gemini-3.5-flash-lite`, 4881 ms, token vào/ra 42/93, `attempts=1`, câu trả lời tiếng Việt về a/an có ví dụ "an hour".
  - pytest vẫn báo **failed**, nhưng lỗi nằm ở bước *in* câu trả lời: `UnicodeEncodeError`, vì console Git Bash dùng cp1252 không in được tiếng Việt. Lỗi không đến từ API.
  - Không gọi lại để tiết kiệm hạn mức. README thêm `$env:PYTHONIOENCODING = "utf-8"` vào hướng dẫn smoke.
- Ca `structured` (có `PYTHONIOENCODING=utf-8`): Google trả **HTTP 503 UNAVAILABLE** (quá tải phía nhà cung cấp).
  - Backend chuẩn hóa đúng thành `LLMProviderError` (`llm_provider_error`).
  - Theo lựa chọn của người dùng, không dùng lời gọi thứ 3. Structured output đã chạy thành công ở Buổi 2 (xem mục Buổi 2 ở trên).

**D. Bản sao sạch theo README** (người dùng cho phép phương án dùng chung PostgreSQL)

- Chép đúng các file sẽ commit (`git ls-files -co --exclude-standard`, không có `.env`, `.venv`, `node_modules`, `dist`) sang thư mục tạm trong scratchpad.
- `.env` tạm tạo từ `.env.example`:
  - user và mật khẩu DB lấy từ `.env` thật;
  - `POSTGRES_DB` = **DB test**, thay cho "DB chính" để không chạm DB chính thật;
  - `JWT_SECRET` sinh mới;
  - `LLM_PROVIDER=fake`, không có key Gemini.
- Các bước:

  | Bước README | Kết quả |
  |---|---|
  | 1: `py -3.13 -m venv`, `pip install -r backend/requirements-dev.txt` | exit 0 (Python 3.13.11) |
  | 3: `docker compose up` | **Bỏ qua**: dùng chung container đang chạy (trùng cổng 5432). `docker-compose.yml`/`docker/` không đổi từ commit 836a645 và đã chạy được trên bản sao sạch ở Tuần 2 (cổng 5433). |
  | 4: `alembic upgrade head`, `alembic -x db=test upgrade head`, `alembic current` | `dfd85f565969 (head)` |
  | 4: `load_placement.py --target main --dry-run` | 30 câu, không ghi |
  | 5: `uvicorn` (cổng 8011 vì 8000 đang bận) | `/health` → `{"status":"ok"}`, `/docs` → 200 |
  | 6: `npm ci` | 0 vulnerabilities |
  | 6: `npm test` | 13/13 |
  | 6: `npm run build` | pass |
  | 7: `pytest` (đặt `POSTGRES_DB` thành tên DB không tồn tại để chắc chắn không chạm DB chính) | **370 passed, 1 skipped** |
- Thư mục tạm đã xóa, vì `.env` tạm chứa mật khẩu DB.
- DB test sau khi chạy: 0 user, 0 tin nhắn, 0 câu hỏi, 0 lượt placement.
- DB chính chỉ đọc số dòng: 1 user, 20 tin nhắn, 30 câu hỏi, 1 lượt placement, là dữ liệu từ lần người dùng tự thử trên trình duyệt.
- README không có lệnh sai. Các điểm đã sửa trong README:
  - dòng trạng thái lỗi thời ("chat và placement chưa có");
  - thiếu yêu cầu phiên bản Node cho `npm test`;
  - thiếu `PYTHONIOENCODING` cho smoke test;
  - mục Kiểm thử chưa có `npm test` và test đầu-cuối.

**E. Tài liệu**

- README: dòng trạng thái, **Node ≥ 22.18** cho `npm test`, smoke test, mục Kiểm thử, bảng Cấu trúc.
  - Mốc 22.18 theo tài liệu phát hành Node: chạy trực tiếp `.ts` không cần cờ từ 23.6 và được đưa về 22.18. Claude chỉ kiểm chứng trên **24.15**.
- `docs/ARCHITECTURE.md`:
  - mục mới "Luồng chat với gia sư AI (Tuần 3) và điểm nối RAG (Tuần 4)", gồm 7 bước của `send_message` và chỗ chèn bước truy xuất giữa bước chuẩn bị prompt và bước gọi LLM (chưa cài đặt gì);
  - phần frontend cập nhật `npm test` và khóa đổi phiên.
- `.env.example`: đối chiếu với `Settings`, đủ tên biến, không cần sửa.
  - `GEMINI_*` được đọc riêng trong `app/llm/gemini.py`.
  - `EMBEDDING_MODEL` và `QDRANT_URL` để dành cho Tuần 4.
  - `APP_NAME` là hằng nội bộ, không cần cấu hình.

### Người dùng tự báo

- Ảnh chụp trang chat ở chế độ `fake`: tin và trả lời hiện đúng thứ tự, có 2 thông báo, có bộ đếm `0/2000` (đã ghi ở Buổi 6).
- 9 mục thử trên trình duyệt trong `WEEK3_ACCEPTANCE.md`: **chưa có báo cáo**.

### Chưa kiểm chứng

- Toàn bộ thao tác trên trình duyệt (9 mục trong `WEEK3_ACCEPTANCE.md`).
- Structured output thật ở Buổi 7 (Google trả 503); lần gần nhất chạy được là Buổi 2.
- Chất lượng câu trả lời thật **theo trình độ** (A1 so với B1): chưa đánh giá có hệ thống; để dành cho Tuần 7.
- `npm test` trên Node 22.18–23.x (chỉ chạy trên 24.15).
- Bước `docker compose up` trên bản sao sạch ở Buổi 7 (lý do ở mục D).

## Tuần 4 — RAG (2026-11-27 → 2026-11-28)

Người dùng đồng ý tất cả các mục của Bước 0: commit Tuần 3, cài dependency, tải BGE-M3, Qdrant, migration DB chính, tối đa 10 lời gọi Gemini, commit Tuần 4. Không sửa `.env`.

Bảng nghiệm thu: `docs/WEEK4_ACCEPTANCE.md`. Số đo: `experiments/README.md`.

### Claude đã chạy

- **Bước 0:**
  - Commit Tuần 3: `87780c5`.
  - `pip install --dry-run` trên Python 3.13.11 phân giải được 35 gói, tải khoảng 225 MB (đo bằng HEAD): `torch 2.15.0+cpu` (127 MB), `sentence-transformers 6.3.0`, `qdrant-client 1.20.0`.
  - Qdrant ổn định mới nhất là v1.20.2 (GitHub release 2026-11-16; image khoảng 74 MB).
  - BGE-M3 (MIT, revision `5617a9f…`): khoảng 2,30 GB nếu bỏ `onnx/`.
  - Máy: ổ C còn 29 GB, ổ F còn 296 GB → cache model đặt ở `F:\AI_Language_Tutor\models\hf`.
- **Cài đặt:**
  - Đã cài 3 gói vào `.venv`; `pip check` không lỗi. Phiên bản ghim trong `backend/requirements.txt`, có dòng `--extra-index-url` của PyTorch CPU.
  - Tải model mất 41 giây, chiếm 2,2 GB trong `models/hf` (Git bỏ qua).
  - Qdrant: `docker pull qdrant/qdrant:v1.20.2`, thêm service vào compose (chỉ mở `127.0.0.1:6333`, volume `qdrantdata`, healthcheck `/readyz` qua bash `/dev/tcp`, tắt telemetry). Trạng thái healthy.
- **Bước 1 — BGE-M3 trên CPU, 3 lần đo** (`experiments/bge_m3_cpu_benchmark.json`):

  | Chỉ số | Kết quả |
  |---|---|
  | Nhúng 1 truy vấn p95 | 109,8 / 66,4 / 63,8 ms |
  | Nhúng 1 truy vấn p50 | 82,1 / 60,7 / 59,1 ms |
  | RAM đỉnh | 2,07–2,08 GB |
  | Nhúng 45 văn bản | 10,5–12,3 s |
  | Tải model | 10–14 s |
  | Vector | 1024 chiều |

  → **Cổng đạt** (ngưỡng: p95 2000 ms, RAM 6 GB).
  - Lần đo đầu báo RAM = 0 do script khai báo sai kiểu handle 64-bit. Đã sửa và đo lại cả 3 lần.
- **Bước 2 — corpus:**
  - Thêm 18 bài nháp: A1 thêm 6, A2 thêm 5, B1 thêm 7 → tổng 33 bài, 11/11/11. Bài mới dài nhất 118 từ.
  - `git diff` chỉ có dòng thêm (216 dòng): 15 bài cũ giữ nguyên từng byte.
  - Từ khóa tiếng Việt để trong file riêng `keywords_vi_v1.json` (CHƯA DUYỆT).
  - Validator mới kiểm quy ước id, số từ ≤ 160, nội dung gần trùng (Jaccard ≥ 0,6) và file từ khóa: 33 bài, 0 lỗi; có thêm 2 test.
  - Dữ liệu đánh giá và split không đổi (`git diff data/evaluation` rỗng).
- **Bước 3–4:**
  - `backend/app/retrieval/` (types, tokenizer, corpus/chunker, bm25, rrf, embedder, dense, hybrid, service, citations).
  - Khối `retrieval` trong `languages/en.yaml`; prompt `prompts/en/tutor_rag.md`.
  - Migration `a4c9e2f17b30` thêm `rag_mode`, `sources`, `rag_fallback` vào `chat_messages` (dùng lại cột `citations` đã có).
    - DB test: upgrade → check → downgrade → upgrade → check, đều đạt.
    - **DB chính: upgrade** (được phép), sau đó `check` không lệch.
  - API: trường `rag_mode` tùy chọn, `GET /chat/rag-config`, `sources` trong tin nhắn.
  - Giao diện: ô chọn chế độ, khung nguồn có `<details>`, các ghi chú hạ cấp và không trích dẫn. `lib/rag.ts` có 4 test.
- **Lỗi thật đã tìm và sửa:**
  - Chỉ số truy xuất đúng nhưng mỗi truy vấn dense mất khoảng 2,2 giây.
  - Đo từng phần: nhúng 111 ms, mỗi lời gọi Qdrant khoảng 2 giây. Nguyên nhân: `.env` có `QDRANT_URL=http://localhost:6333`, và Windows thử IPv6 trước.
  - Code nay tự đổi `localhost` thành `127.0.0.1` (không sửa `.env`). Sau khi sửa: p50 khoảng 240 ms.
- **Nạp index:** `scripts/index_corpus.py --keywords both` → `lessons_en` và `lessons_kwvi_en`, mỗi collection thêm 33 chunk. Chạy lại: "không đổi 33", tức là idempotent.
- **Bước 5 — đánh giá trên dev:**
  - `--split test` bị **từ chối**.
  - Có 2 lần chạy với cùng cấu hình. Lần 1 có độ trễ sai do lỗi localhost nói trên; lần 2 có độ trễ đúng; chỉ số truy xuất hai lần giống hệt. Cả hai được ghi trong `retrieval_runs.jsonl`.
  - Kết quả (index_text gốc): dense R@1/3/5 = 0,75/0,95/1,00, MRR 0,863; hybrid 0,80/1,00/1,00, MRR 0,883; BM25 MRR 0,666.
  - Thêm keywords_vi: dense MRR 0,938, nhưng hybrid R@3 giảm xuống 0,90. **Không bật**: có nguy cơ rò rỉ do cùng tác giả với truy vấn dev.
  - Không chỉnh siêu tham số nào.
- **Test:** thêm `test_retrieval.py` (17 test) và `test_chat_rag.py` (9 test).
  - `pytest` không mạng, không key: **398 passed, 5 skipped**; skipped đều là smoke, mặc định tắt.
  - `npm test` 17/17; `npm run build` đạt.
- **Làm hỏng có chủ đích (6 chỗ, khôi phục xong đều `cmp` khớp):**

  | Chỗ làm hỏng | Kết quả |
  |---|---|
  | RRF `k+rank` → `k*rank` | 3 failed |
  | BM25 bỏ lọc ngôn ngữ | 1 failed |
  | Dense bỏ lọc ngôn ngữ | 1 failed |
  | Không loại trích dẫn ngoài tập truy xuất | 4 failed |
  | Đảo dấu IDF | 5 failed |
  | Chat không hạ cấp khi truy xuất lỗi | 1 failed |
- **Smoke test có tài nguyên thật** (Qdrant thật, BGE-M3 thật):
  - `RUN_RAG_SMOKE=1`: truy xuất 2/2 đạt.
  - `RUN_RAG_SMOKE_LLM=1`: chat qua API trên DB test với **2 lời gọi Gemini** (tổng tuần 2/10). Hybrid và dense đều 200, nguồn [1] đúng bài (articles, passive), `has_citations=true`, không hạ cấp. Câu trả lời tiếng Việt có trích dẫn `[1]`.
- **Quét secret:** key Gemini, JWT secret, mật khẩu DB đều 0 lần trong file sẽ commit, `dist` và lịch sử Git; 0 chuỗi `AIza…`; `.env` không được Git theo dõi. Log RAG chỉ ghi metadata.

### Người dùng tự báo

- Chưa có báo cáo cho Tuần 4.

### Chưa kiểm chứng

- Thao tác trên trình duyệt: ô chọn chế độ, khung nguồn, ghi chú hạ cấp khi dừng Qdrant, màn hình 360px.
- Chất lượng ngữ pháp của 18 bài mới và của từ khóa: **CHƯA DUYỆT**, cần người kiểm.
- Chất lượng câu trả lời RAG thật ngoài 2 câu smoke: chưa đánh giá có hệ thống (faithfulness, độ đúng của trích dẫn) — để dành cho Tuần 7.
- Hạ cấp khi dừng Qdrant thật: mới kiểm bằng test (retriever ném lỗi), chưa dừng container thật trong lúc chat.
