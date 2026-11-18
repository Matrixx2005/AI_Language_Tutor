# Kết quả kiểm tra môi trường

<!-- check_env:AUTO_START -->
## Kết quả tự động (scripts/check_env.py)

Chạy lúc: 2026-11-18 21:09

| Mục | Kết quả |
| --- | --- |
| Python đang chạy | 3.13.11 |
| Đường dẫn Python | F:\AI_Language_Tutor\.venv\Scripts\python.exe |
| Đang trong venv | có |
| Yêu cầu Python >= 3.13 | ĐẠT |
| Hệ điều hành | Windows 11 (AMD64) |
| RAM | 31.6 GB tổng, 15.0 GB trống |
| Ổ đĩa dự án trống | 295.7 GB |
| git | git version 2.54.0.windows.1 |
| node | v24.15.0 |
| npm | 11.12.1 |
| docker | KHÔNG TÌM THẤY |
| docker compose | KHÔNG TÌM THẤY |
| Các bản Python (py -0p) | -V:3.13 *        C:\Users\Admin\AppData\Local\Programs\Python\Python313\python.exe |
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
