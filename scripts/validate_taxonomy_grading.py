"""Kiểm tra danh mục lỗi (languages/<code>.yaml → error_taxonomy) và bộ đánh giá bộ chấm data/evaluation/grading_v1.json.

  python scripts/validate_taxonomy_grading.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.core.languages import get_language_config  # noqa: E402

GRADING = ROOT / "data" / "evaluation" / "grading_v1.json"
LESSONS = ROOT / "data" / "processed" / "grammar_lessons_v1.json"
VERDICTS = {"correct", "partially", "incorrect"}
RULE_EXPECTED = {"correct", "incorrect", "needs_llm"}


def validate_taxonomy(config, lesson_ids: set[str]) -> list[str]:
    errors = []
    ids = [t.id for t in config.error_taxonomy]
    if len(ids) != len(set(ids)):
        errors.append("taxonomy: id trùng")
    if "other" not in ids:
        errors.append("taxonomy: thiếu 'other'")
    if not 15 <= len(ids) <= 25:
        errors.append(f"taxonomy: {len(ids)} loại (cần khoảng 15–20)")
    for t in config.error_taxonomy:
        for topic in t.topics:
            if topic not in lesson_ids:
                errors.append(f"taxonomy: {t.id} tham chiếu bài không tồn tại {topic}")
        if not t.name_vi.strip() or not t.example_wrong.strip() or not t.example_right.strip():
            errors.append(f"taxonomy: {t.id} thiếu tên hoặc ví dụ")
    return errors


def validate_grading(payload: object, config) -> list[str]:
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        return ["grading: cần object có 'items'"]
    errors, ids = [], set()
    items = payload["items"]
    for it in items:
        iid = it.get("item_id")
        if iid in ids:
            errors.append(f"grading: trùng {iid}")
        ids.add(iid)
        if it.get("exercise_type") not in {"error_correction", "translate_vi_en"}:
            errors.append(f"grading: {iid} dạng bài không hợp lệ")
        if it.get("expected_verdict") not in VERDICTS or it.get("rule_expected") not in RULE_EXPECTED:
            errors.append(f"grading: {iid} nhãn không hợp lệ")
        et = it.get("expected_error_type")
        if et is not None and et not in config.error_type_ids:
            errors.append(f"grading: {iid} loại lỗi ngoài taxonomy {et}")
        if it.get("author") not in {"claude-draft", "human"}:
            errors.append(f"grading: {iid} author không hợp lệ")
        if not str(it.get("learner_answer", "")).strip():
            errors.append(f"grading: {iid} thiếu câu trả lời")
    if len(items) < 40:
        errors.append(f"grading: chỉ có {len(items)} mục (< 40)")
    if sum(1 for it in items if it.get("case") == "injection") < 5:
        errors.append("grading: cần ≥ 5 ca prompt-injection")
    return errors


def main() -> int:
    config = get_language_config("en")
    lesson_ids = {r["document_id"] for r in json.loads(LESSONS.read_text(encoding="utf-8"))}
    errors = validate_taxonomy(config, lesson_ids) + validate_grading(json.loads(GRADING.read_text(encoding="utf-8")), config)
    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1
    covered = {t for et in config.error_taxonomy for t in et.topics}
    print(f"Taxonomy passed: {len(config.error_taxonomy)} loại, gắn {len(covered)}/{len(lesson_ids)} bài học. "
          f"Grading v1 passed: {len(json.loads(GRADING.read_text(encoding='utf-8'))['items'])} mục.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
