"""B7.1: thống kê chất lượng ngân hàng bài tập (đọc DB) → experiments/exercises_<thời gian>.json,
và tạo docs/EXERCISE_REVIEW.md (mẫu ngẫu nhiên có seed ≥ 40 bài validated) để NGƯỜI duyệt. Không gọi LLM.

  python scripts/eval_exercises.py [--target main|test] [--sample 40] [--seed 20261128]
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.exercises.normalize import words  # noqa: E402
from app.models import Exercise  # noqa: E402


def main_text(ex: Exercise) -> str:
    p = ex.prompt_payload or {}
    return p.get("question") or p.get("sentence") or " ".join(p.get("tokens") or []) or p.get("source_vi") or ""


def stats(rows: list[Exercise]) -> dict:
    total = len(rows)
    validated = [r for r in rows if r.validation_status == "validated"]
    by = lambda key: {k: {"total": len(v), "validated": sum(1 for r in v if r.validation_status == "validated"),  # noqa: E731
                          "pass_rate": round(sum(1 for r in v if r.validation_status == "validated") / len(v), 4)}
                      for k, v in sorted(_group(rows, key).items())}
    checked = [r for r in rows if (r.generation_meta or {}).get("independent_check") is not None]
    matched = [r for r in checked if r.generation_meta["independent_check"]]
    lengths = [len(words(main_text(r))) for r in validated]
    per_doc = Counter(r.document_id for r in validated)
    return {
        "total": total, "validated": len(validated), "rejected": total - len(validated),
        "pass_rate": round(len(validated) / total, 4) if total else 0.0,
        "by_type": by("exercise_type"), "by_level": by("level_code"),
        "reject_reasons": dict(Counter(reason for r in rows for reason in (r.reject_reasons or []))),
        "independent_checked": len(checked), "independent_match_rate": round(len(matched) / len(checked), 4) if checked else None,
        "validated_per_lesson": {"min": min(per_doc.values()) if per_doc else 0, "max": max(per_doc.values()) if per_doc else 0,
                                 "lessons_with_ge_3": sum(1 for v in per_doc.values() if v >= 3), "lessons_covered": len(per_doc)},
        "length_words": {"mean": round(statistics.mean(lengths), 1) if lengths else None, "max": max(lengths) if lengths else None},
        "review_status": dict(Counter(r.review_status for r in rows)),
        "note": "Tỷ lệ trùng lặp: bài trùng bị chặn bởi content_hash (không lưu); xem duplicates_in_run/skipped_existing trong exercise_generation_*.json.",
    }


def _group(rows, key):
    out = defaultdict(list)
    for r in rows:
        out[getattr(r, key)].append(r)
    return out


def review_doc(sample: list[Exercise], seed: int) -> str:
    lines = [
        "# Duyệt mẫu bài tập (Tuần 5B)", "",
        f"Mẫu {len(sample)} bài **validated** chọn ngẫu nhiên (seed {seed}) từ bảng `exercises`. Bài do AI (Gemini) soạn, đã qua bộ kiểm tra tự động",
        "và (với mcq/cloze/sửa lỗi/sắp xếp) kiểm tra độc lập — đó KHÔNG phải đảm bảo đúng. **Claude không tự điền kết quả duyệt.**", "",
        "Checklist mỗi bài: (1) đáp án duy nhất/đúng, (2) câu đúng ngữ pháp và tự nhiên, (3) đúng trình độ, (4) giải thích đúng.",
        "Ghi: `đạt` hoặc `sai: <lý do>` vào cột Kết quả; cuối file ghi người duyệt + ngày.", "",
        "| # | exercise_id | Dạng | Cấp | Bài học | Đề | Đáp án | Giải thích | Kết quả (người duyệt) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    clean = lambda s: str(s).replace("|", "/").replace("\n", " ")  # noqa: E731
    for n, ex in enumerate(sample, 1):
        key = ex.answer_key or {}
        answer = key.get("answer") or key.get("reference") or " / ".join(key.get("accepted", []))
        lines.append(f"| {n} | `{str(ex.exercise_id)[:8]}` | {ex.exercise_type} | {ex.level_code} | {ex.document_id} | "
                     f"{clean(json.dumps(ex.prompt_payload, ensure_ascii=False))} | {clean(answer)} | {clean(ex.explanation)} | |")
    lines += ["", "Người duyệt: ____________ · Ngày: ____________"]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", choices=["main", "test"], default="main")
    parser.add_argument("--sample", type=int, default=40)
    parser.add_argument("--seed", type=int, default=20261128)
    args = parser.parse_args()
    engine = create_engine(get_settings().database_url(test=args.target == "test"))
    with Session(engine) as db:
        rows = list(db.scalars(select(Exercise).where(Exercise.language_code == "en").order_by(Exercise.created_at, Exercise.exercise_id)))
        result = stats(rows)
        validated = [r for r in rows if r.validation_status == "validated"]
        sample = random.Random(args.seed).sample(validated, min(args.sample, len(validated)))
        (ROOT / "docs" / "EXERCISE_REVIEW.md").write_text(review_doc(sample, args.seed), encoding="utf-8")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (ROOT / "experiments" / f"exercises_{stamp}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
