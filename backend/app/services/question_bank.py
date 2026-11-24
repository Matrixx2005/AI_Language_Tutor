"""Nạp ngân hàng câu hỏi placement từ file JSON vào bảng `questions`.

- Kiểm tra schema TRƯỚC (dùng lại scripts/validate_evaluation.validate_placement); có lỗi thì không ghi gì.
- Idempotent: khớp theo `external_id` (= question_id trong file), chỉ thêm mới hoặc cập nhật khi khác.
- Chỉ đọc file nguồn, không bao giờ sửa.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import PROJECT_ROOT
from app.models import Question

DEFAULT_PLACEMENT_FILE = PROJECT_ROOT / "data" / "evaluation" / "placement_v1.json"


class QuestionBankError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        super().__init__(f"{len(errors)} lỗi dữ liệu")
        self.errors = errors


@dataclass(frozen=True)
class LoadReport:
    question_set: str
    inserted: int
    updated: int
    unchanged: int

    @property
    def total(self) -> int:
        return self.inserted + self.updated + self.unchanged


def _validator():
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.validate_evaluation import validate_placement

    return validate_placement


def read_placement_file(path: Path = DEFAULT_PLACEMENT_FILE) -> list[dict]:
    try:
        records = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise QuestionBankError([f"không đọc được {path.name}: {type(exc).__name__}"]) from None
    errors = _validator()(records)
    if errors:
        raise QuestionBankError(errors)
    return records


def _fields(record: dict, question_set: str) -> dict:
    return {
        "question_set": question_set,
        "language_code": record["language_code"],
        "level_code": record["level_code"],
        "category": record["category"],
        "topic": record["topic"],
        "question_type": "multiple_choice",
        "prompt": record["question_text"],
        "options": list(record["options"]),
        "correct_answer": record["correct_answer"],
        "explanation": record.get("explanation"),
    }


def load_questions(db: Session, records: list[dict], question_set: str) -> LoadReport:
    """Ghi vào session; người gọi quyết định commit (script) hay rollback (dry-run, test)."""
    existing = {
        q.external_id: q
        for q in db.scalars(select(Question).where(Question.external_id.in_([r["question_id"] for r in records])))
    }
    inserted = updated = unchanged = 0
    for record in records:
        values = _fields(record, question_set)
        current = existing.get(record["question_id"])
        if current is None:
            db.add(Question(external_id=record["question_id"], **values))
            inserted += 1
        elif any(getattr(current, key) != value for key, value in values.items()):
            for key, value in values.items():
                setattr(current, key, value)
            updated += 1
        else:
            unchanged += 1
    db.flush()
    return LoadReport(question_set, inserted, updated, unchanged)
