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
