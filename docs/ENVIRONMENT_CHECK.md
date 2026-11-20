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
