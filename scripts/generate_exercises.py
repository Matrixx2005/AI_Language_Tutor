"""Sinh ngân hàng bài tập từ corpus (Tuần 5B).

  python scripts/generate_exercises.py --dry-run                  # đếm số lời gọi dự kiến, không gọi API
  python scripts/generate_exercises.py --max-calls 40             # sinh (mặc định ghi DB chính), kiểm tra, kiểm tra độc lập
  python scripts/generate_exercises.py --top-up                   # vòng bù cho bài học có < 3 bài validated
  python scripts/generate_exercises.py --provider fake --target test   # chạy thử luồng, không mạng

Mỗi bài học: 1 lời gọi sinh `--per-lesson` bài (xoay vòng 5 dạng) → bộ kiểm tra thuần → kiểm tra độc lập
(LLM giải không kèm đáp án, gộp 5 bài/lời gọi; translate không áp dụng) → lưu DB: validated hoặc rejected + lý do.
Không giữ giao dịch DB khi gọi LLM. LLM chạy với max_retries=0 và không model dự phòng: 1 lời gọi = 1 request thật.
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

from llm_budget import BudgetedLLM, BudgetStop  # noqa: E402
from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.languages import get_language_config  # noqa: E402
from app.exercises.validators import content_hash, validate_draft  # noqa: E402
from app.llm.errors import LLMError  # noqa: E402
from app.llm.types import ChatMessage, LLMRequest  # noqa: E402
from app.models import Exercise  # noqa: E402
from app.retrieval.corpus import load_lessons  # noqa: E402
from app.services.exercise_generation import (  # noqa: E402
    SOLVABLE, GenerationOutput, SolveOutput, build_generation_request, build_solve_request, generation_meta,
    independent_matches, to_draft, types_for,
)

CHECK_BATCH = 5


def make_llm(provider: str):
    from app.llm import build_llm_service

    settings = get_settings().model_copy(update={"llm_max_retries": 0, "llm_fallback_model_ids": "",
                                                  "llm_provider": provider or get_settings().llm_provider})
    if settings.llm_provider == "fake":
        return fake_generation_llm()
    return build_llm_service(settings)


def fake_generation_llm():
    """FakeLLM trả JSON hợp lệ cho mọi dạng (kèm 1 bài hỏng cố ý) — chỉ để kiểm thử luồng, không phải nội dung thật."""
    from app.llm.fake import FakeLLM, Reply
    from app.llm.service import LLMService

    class FakeGen(FakeLLM):
        def generate(self, request, *, model, timeout_seconds):
            if "Solve" in request.messages[0].content:
                ids = [line.split(" ")[0] for line in request.system_prompt.split("<<<BAI_TAP>>>")[1].split("<<<HET_BAI_TAP>>>")[0].strip().splitlines()]
                self._steps.append(Reply(json.dumps({"answers": [{"id": i, "answer": "AMBIGUOUS"} for i in ids]})))
            else:
                n = int(request.system_prompt.split("Create exactly ")[1].split(" ")[0])
                doc = request.system_prompt.split("Lesson: ")[1].split(" ")[0]
                items = [{"exercise_type": "mcq", "error_type": "other", "question": f"Fake {doc} ___ {i}?",
                          "options": ["one", "two", "three", "four"], "answer": "two", "explanation_vi": "Giả lập."} for i in range(n - 1)]
                items.append({"exercise_type": "mcq", "error_type": "other", "question": f"Broken {doc}?",
                              "options": ["x", "x", "y", "z"], "answer": "x", "explanation_vi": "Hỏng cố ý."})
                self._steps.append(Reply(json.dumps({"items": items})))
            return super().generate(request, model=model, timeout_seconds=timeout_seconds)

    llm = LLMService(FakeGen(), model="fake-model", max_retries=0, sleep=lambda _: None)
    return llm


def run(*, target: str, provider: str, max_calls: int, check_max_calls: int, per_lesson: int, top_up: bool, dry_run: bool,
        independent: bool, lessons_filter: list[str] | None = None, engine=None, language: str = "en") -> dict:
    config = get_language_config(language)
    settings = get_settings()
    engine = engine or create_engine(settings.database_url(test=(target == "test")))
    lessons = [x for x in load_lessons(language) if not lessons_filter or x.document_id in lessons_filter]
    lesson_ids = {x.document_id for x in load_lessons(language)}
    llm = None if dry_run else make_llm(provider)
    gen = BudgetedLLM(llm, f"exercise_generate_{'fake' if provider == 'fake' else 'gemini'}", max_calls=max_calls, dry_run=dry_run,
                      per_minute=0 if provider == "fake" else 8)
    check = BudgetedLLM(llm, f"exercise_check_{'fake' if provider == 'fake' else 'gemini'}", max_calls=check_max_calls, dry_run=dry_run,
                        per_minute=0 if provider == "fake" else 8)

    with Session(engine) as db:
        existing = {h for (h,) in db.execute(select(Exercise.content_hash).where(Exercise.language_code == language))}
        validated_per_doc = Counter(d for (d,) in db.execute(select(Exercise.document_id).where(
            Exercise.language_code == language, Exercise.validation_status == "validated")))
    report = {"started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "target": target, "provider": provider,
              "dry_run": dry_run, "lessons": 0, "drafts": 0, "inserted_validated": 0, "inserted_rejected": 0,
              "skipped_existing": 0, "duplicates_in_run": 0, "reject_reasons": Counter(), "independent": Counter(),
              "by_type": Counter(), "stopped": None, "llm_errors": []}
    pending: list = []  # (lesson, draft, reasons, model)
    try:
        for index, lesson in enumerate(lessons):
            if top_up and validated_per_doc.get(lesson.document_id, 0) >= 3:
                continue
            types = types_for(index + (7 if top_up else 0), per_lesson, config.exercises.types)
            request = build_generation_request(lesson, config, types)
            if top_up:
                request = LLMRequest(request.system_prompt, (ChatMessage("user", "Create the exercises now. (round 2: new sentences)"),),
                                     request.response_schema, request.max_output_tokens)
            try:
                record = gen.generate(request)
            except LLMError as error:  # một bài học lỗi (schema, timeout...) không làm dừng cả lô
                report["llm_errors"].append({"document_id": lesson.document_id, "stage": "generate", "code": error.code})
                continue
            report["lessons"] += 1
            if record is None:
                continue
            output = GenerationOutput.model_validate(record["parsed"])
            for item in output.items:
                d = to_draft(item, lesson)
                h = content_hash(language, d.exercise_type, d.payload, config)
                if h in existing:
                    report["skipped_existing"] += 1
                    continue
                reasons = validate_draft(d, config, lesson_ids, existing)
                existing.add(h)
                report["drafts"] += 1
                pending.append([lesson, d, reasons, record["model"], h, None])
        # Kiểm tra độc lập: chỉ bài đã qua bộ kiểm tra, dạng giải được.
        if independent:
            todo = [p for p in pending if not p[2] and p[1].exercise_type in SOLVABLE]
            for start in range(0, len(todo), CHECK_BATCH):
                batch = todo[start:start + CHECK_BATCH]
                items = [(f"q{n}", p[1]) for n, p in enumerate(batch, 1)]
                try:
                    record = check.generate(build_solve_request(items, config))
                except LLMError as error:
                    report["llm_errors"].append({"batch": start, "stage": "check", "code": error.code})
                    continue
                if record is None:
                    continue
                matches = independent_matches(items, SolveOutput.model_validate(record["parsed"]), config)
                for (item_id, _), p in zip(items, batch):
                    p[5] = matches[item_id]
                    if not matches[item_id]:
                        p[2] = ["independent_check_mismatch"]
    except BudgetStop as stop:
        report["stopped"] = str(stop)
    # Ghi DB (giao dịch ngắn, không có lời gọi LLM nào bên trong).
    if not dry_run:
        with Session(engine) as db:
            for lesson, d, reasons, model, h, independent_ok in pending:
                if independent and not reasons and d.exercise_type in SOLVABLE and independent_ok is None:
                    continue  # chưa kiểm tra độc lập (dừng giữa chừng) → để lần chạy sau
                status = "rejected" if reasons else "validated"
                meta = generation_meta(model) | {"independent_check": independent_ok}
                db.add(Exercise(language_code=language, level_code=d.level_code, exercise_type=d.exercise_type, document_id=d.document_id,
                                source_document_ids=[d.document_id], topic=lesson.topic, error_type=d.error_type if d.error_type in config.error_type_ids else "other",
                                prompt_payload=d.payload, answer_key=d.answer_key, explanation=d.explanation, generation_meta=meta,
                                content_hash=h, validation_status=status, reject_reasons=reasons))
                report["inserted_validated" if status == "validated" else "inserted_rejected"] += 1
                report["by_type"][f"{d.exercise_type}:{status}"] += 1
                report["reject_reasons"].update(reasons)
                if independent_ok is not None:
                    report["independent"]["match" if independent_ok else "mismatch"] += 1
            db.commit()
    report["calls"] = {"generate": gen.report(), "check": check.report()}
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", choices=["main", "test"], default="main")
    parser.add_argument("--provider", choices=["gemini", "fake"], default="gemini")
    parser.add_argument("--max-calls", type=int, default=40)
    parser.add_argument("--check-max-calls", type=int, default=40)
    parser.add_argument("--per-lesson", type=int, default=4)
    parser.add_argument("--top-up", action="store_true")
    parser.add_argument("--no-independent-check", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--lessons", nargs="*")
    args = parser.parse_args()
    independent = get_settings().exercise_independent_check and not args.no_independent_check
    report = run(target=args.target, provider=args.provider, max_calls=args.max_calls, check_max_calls=args.check_max_calls,
                 per_lesson=args.per_lesson, top_up=args.top_up, dry_run=args.dry_run, independent=independent, lessons_filter=args.lessons)
    out = {k: (dict(v) if isinstance(v, Counter) else v) for k, v in report.items()}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if not args.dry_run:
        exp = ROOT / "experiments"
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        (exp / f"exercise_generation_{stamp}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if not report["stopped"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
