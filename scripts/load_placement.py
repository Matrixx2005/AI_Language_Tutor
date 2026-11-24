"""Nạp ngân hàng câu hỏi placement vào DB (không sửa file nguồn).

Chạy từ thư mục gốc dự án:
    python scripts/load_placement.py --target test             # DB test
    python scripts/load_placement.py --target main --dry-run   # xem trước, không ghi
    python scripts/load_placement.py --target main             # DB chính (cần migration dfd85f565969)

Bắt buộc ghi rõ --target để không lỡ tay nạp vào DB chính.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.exc import OperationalError, ProgrammingError  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.services.question_bank import DEFAULT_PLACEMENT_FILE, QuestionBankError, load_questions, read_placement_file  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Nạp câu hỏi placement vào bảng questions.")
    parser.add_argument("--target", choices=["test", "main"], required=True, help="DB đích")
    parser.add_argument("--input", type=Path, default=DEFAULT_PLACEMENT_FILE, help="file JSON nguồn")
    parser.add_argument("--dry-run", action="store_true", help="chỉ báo cáo, không ghi DB")
    args = parser.parse_args()

    try:
        records = read_placement_file(args.input)
    except QuestionBankError as error:
        for message in error.errors:
            print(f"ERROR: {message}", file=sys.stderr)
        print("Không nạp gì: dữ liệu chưa hợp lệ.", file=sys.stderr)
        return 1

    settings = get_settings()
    engine = create_engine(settings.database_url(test=args.target == "test"), connect_args={"connect_timeout": 10})
    question_set = args.input.stem
    try:
        with Session(engine) as db:
            report = load_questions(db, records, question_set)
            if args.dry_run:
                db.rollback()
            else:
                db.commit()
    except OperationalError:
        print(f"ERROR: không kết nối được DB ({args.target}). PostgreSQL đang chạy chưa? "
              "Thử: docker compose up -d --wait", file=sys.stderr)
        return 2
    except ProgrammingError:
        print("ERROR: DB chưa có bảng questions. Chạy migration trước: cd backend; alembic upgrade head",
              file=sys.stderr)
        return 2
    finally:
        engine.dispose()
    mode = "DRY-RUN (không ghi)" if args.dry_run else "đã ghi"
    print(f"[{args.target}] {question_set}: {report.total} câu — thêm {report.inserted}, "
          f"cập nhật {report.updated}, không đổi {report.unchanged} — {mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
