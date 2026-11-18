# AI Language Tutor

Hệ thống hỗ trợ học tiếng Anh A1–B1 cho người Việt, dùng Retrieval-Augmented Generation (BM25 + BGE-M3 + RRF), Gemini Flash và cá nhân hóa học tập. Đồ án tốt nghiệp Khoa học máy tính.

Trạng thái: Tuần 1 (thiết kế và chuẩn bị). Kế hoạch: `docs/PROJECT_MASTER_PLAN.md`.

## Thiết lập môi trường (Windows, PowerShell)

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python scripts/check_env.py
```

`check_env.py` chỉ đọc thông tin máy, không cài gì. Kết quả ghi vào phần tự động của `docs/ENVIRONMENT_CHECK.md` (ghi chép tay được giữ nguyên).

## Kiểm thử và validate dữ liệu

```powershell
pytest -q
python scripts/validate_dataset.py
python scripts/validate_evaluation.py
```

## Cấu trúc

- `backend/` — FastAPI (bắt đầu Tuần 2)
- `data/` — dữ liệu thô, đã xử lý, bộ đánh giá
- `docs/` — tài liệu thiết kế và kế hoạch
- `scripts/` — script tiện ích
