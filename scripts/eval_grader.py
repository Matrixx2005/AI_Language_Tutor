"""B7.2: đánh giá bộ chấm LLM trên data/evaluation/grading_v1.json (chỉ các mục cần LLM: rule_expected=needs_llm).

  python scripts/eval_grader.py --dry-run
  python scripts/eval_grader.py --max-calls 40
Nhãn do Claude soạn, CHƯA duyệt bởi người → kết quả chỉ mang tính tham khảo. Không chỉnh prompt theo kết quả quá 1 lần.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

from eval_retrieval import bootstrap_ci  # noqa: E402
from llm_budget import BudgetedLLM, BudgetStop  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.languages import get_language_config  # noqa: E402
from app.exercises.grading import GraderOutput, finalize_llm_grade  # noqa: E402
from app.llm.errors import LLMError  # noqa: E402
from app.services.exercises import build_grader_request  # noqa: E402

GRADING = ROOT / "data" / "evaluation" / "grading_v1.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--max-calls", type=int, default=40)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    config = get_language_config("en")
    items = [i for i in json.loads(GRADING.read_text(encoding="utf-8"))["items"] if i["rule_expected"] == "needs_llm"]
    from app.llm import build_llm_service

    llm = None if args.dry_run else build_llm_service(get_settings().model_copy(update={"llm_max_retries": 0, "llm_fallback_model_ids": ""}))
    budget = BudgetedLLM(llm, "grader_eval", max_calls=args.max_calls, dry_run=args.dry_run)
    rows, errors = [], []
    try:
        for it in items:
            req = build_grader_request(it["exercise_type"], it["prompt"], it["answer_key"], it["level_code"], it["learner_answer"], "en")
            try:
                record = budget.generate(req)
            except LLMError as error:
                errors.append({"item_id": it["item_id"], "code": error.code})
                continue
            if record is None:
                continue
            grade = finalize_llm_grade(GraderOutput.model_validate(record["parsed"]), config)
            predicted_types = sorted({e["error_type"] for e in grade.errors})
            rows.append({"item_id": it["item_id"], "case": it["case"], "type": it["exercise_type"], "expected": it["expected_verdict"],
                         "predicted": grade.verdict, "score": grade.score, "expected_error_type": it["expected_error_type"],
                         "predicted_error_types": predicted_types})
    except BudgetStop as stop:
        print(f"DỪNG: {stop}")
    print(budget.report())
    if args.dry_run or not rows:
        return 0
    exact = [1.0 if r["predicted"] == r["expected"] else 0.0 for r in rows]
    binary = [1.0 if (r["predicted"] == "correct") == (r["expected"] == "correct") else 0.0 for r in rows]
    neg = [r for r in rows if r["expected"] != "correct"]
    pos = [r for r in rows if r["expected"] == "correct"]
    false_accept = [1.0 if r["predicted"] == "correct" else 0.0 for r in neg]
    false_reject = [1.0 if r["predicted"] != "correct" else 0.0 for r in pos]
    typed = [r for r in rows if r["expected_error_type"] and r["expected"] != "correct"]
    type_agree = [1.0 if r["expected_error_type"] in r["predicted_error_types"] else 0.0 for r in typed]
    injection = [r for r in rows if r["case"] == "injection"]
    summary = {
        "n_items": len(rows), "llm_errors": errors,
        "verdict_accuracy_3class": bootstrap_ci(exact), "binary_accuracy_correct_vs_not": bootstrap_ci(binary),
        "false_accept_rate": bootstrap_ci(false_accept) if false_accept else None, "n_negative": len(neg),
        "false_reject_rate": bootstrap_ci(false_reject) if false_reject else None, "n_positive": len(pos),
        "error_type_agreement": bootstrap_ci(type_agree) if type_agree else None, "n_typed": len(typed),
        "injection_resisted": f"{sum(1 for r in injection if r['predicted'] != 'correct')}/{len(injection)}",
        "confusion": dict(Counter(f"{r['expected']}->{r['predicted']}" for r in rows)),
        "caveat": "Mẫu nhỏ; nhãn do Claude soạn, chưa duyệt bởi người; chỉ mang tính tham khảo.",
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = {"run_at": stamp, "prompt_version": "grader_v1", "model_calls": budget.report(), "summary": summary, "rows": rows}
    (ROOT / "experiments" / f"grader_eval_{stamp}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
