"""Nghiệp vụ bài tập: chọn bài, xem bài (KHÔNG có đáp án), nộp/chấm, chấm lại, lịch sử, tổng hợp lỗi, duyệt.

Quy ước: owner check → 404; không giữ giao dịch DB khi gọi LLM (lưu bài làm 'pending' + commit TRƯỚC);
lỗi LLM không làm mất bài làm (POST .../regrade chấm lại, idempotent); log chỉ metadata (không có nội dung bài làm).
"""
from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import limits as limits_module
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.languages import get_language_config
from app.core.limits import AppLimits, local_day_bounds, log_rejection, rate_limit_error, seconds_until_local_midnight
from app.core.prompts import render_prompt
from app.exercises.analysis import AttemptFact, Candidate, ErrorFact, choose_next, summarize
from app.exercises.grading import GraderOutput, LlmGrade, clean_answer, finalize_llm_grade, grade_rule
from app.llm.errors import LLMError
from app.llm.service import LLMService
from app.llm.types import ChatMessage, LLMRequest
from app.models import ErrorEvent, Exercise, ExerciseAttempt, PlacementResult, User
from app.retrieval.corpus import load_lessons

logger = logging.getLogger("app.exercises")
VISIBLE = ("validated",)
SERVICE_BUSY = "Hệ thống đang bận. Bài làm đã được lưu, bạn có thể chấm lại sau."


def _language(user: User) -> str:
    return user.profile.language_code if user.profile else "en"


def _visible_query(language_code: str):
    return select(Exercise).where(
        Exercise.language_code == language_code, Exercise.validation_status.in_(VISIBLE),
        Exercise.review_status != "rejected_by_human",
    )


def public_exercise(ex: Exercise) -> dict:
    """Phần công khai của bài tập — tuyệt đối không có answer_key/explanation."""
    return {
        "exercise_id": ex.exercise_id, "language_code": ex.language_code, "level_code": ex.level_code,
        "exercise_type": ex.exercise_type, "document_id": ex.document_id, "topic": ex.topic,
        "prompt": ex.prompt_payload, "review_status": ex.review_status,
    }


def _lesson_title(language_code: str, document_id: str) -> str:
    try:
        return next((x.title for x in load_lessons(language_code) if x.document_id == document_id), document_id)
    except Exception:
        return document_id


def solution(ex: Exercise) -> dict:
    """Đáp án + giải thích + bài học nguồn — CHỈ dùng sau khi người học đã nộp."""
    key = ex.answer_key or {}
    shown = {"mcq": lambda: [key.get("answer")], "translate_vi_en": lambda: [key.get("reference")]}.get(
        ex.exercise_type, lambda: list(key.get("accepted", [])))()
    return {"correct_answers": [a for a in shown if a], "explanation": ex.explanation,
            "source": {"document_id": ex.document_id, "title": _lesson_title(ex.language_code, ex.document_id)}}


def attempt_view(attempt: ExerciseAttempt, ex: Exercise) -> dict:
    return {
        "attempt_id": attempt.attempt_id, "exercise_id": attempt.exercise_id, "grading_status": attempt.grading_status,
        "graded_by": attempt.graded_by, "is_correct": attempt.is_correct, "score": attempt.score,
        "feedback": attempt.feedback or {}, "error_types": attempt.error_types or [], "created_at": attempt.created_at,
        "answer": attempt.answer, "solution": solution(ex),
    }


def get_exercise(db: Session, user: User, exercise_id: uuid.UUID) -> Exercise:
    ex = db.scalar(_visible_query(_language(user)).where(Exercise.exercise_id == exercise_id))
    if ex is None:
        raise AppError(404, "exercise_not_found", "Không tìm thấy bài tập.")
    return ex


def next_exercise(db: Session, user: User, topic: str | None, exercise_type: str | None) -> Exercise:
    lang = _language(user)
    rows = db.execute(_visible_query(lang).with_only_columns(
        Exercise.exercise_id, Exercise.document_id, Exercise.exercise_type, Exercise.level_code)).all()
    level = user.profile.current_level_code if user.profile else None
    at_level = [r for r in rows if r.level_code == level]
    pool = [Candidate(str(r.exercise_id), r.document_id, r.exercise_type) for r in (at_level or rows)]
    if topic or exercise_type:  # lọc theo yêu cầu trên toàn bộ trình độ nếu cấp hiện tại không có
        pool = [Candidate(str(r.exercise_id), r.document_id, r.exercise_type) for r in rows]
    recent = db.scalars(select(ExerciseAttempt.exercise_id).where(ExerciseAttempt.user_id == user.user_id)
                        .order_by(ExerciseAttempt.created_at.desc()).limit(10)).all()
    week_ago = limits_module.utcnow() - timedelta(days=7)
    recent_errors = db.scalars(select(ErrorEvent.document_id).where(
        ErrorEvent.user_id == user.user_id, ErrorEvent.created_at >= week_ago)).all()
    weak = _placement_weak_topics(db, user, lang)
    attempts_count = db.scalar(select(func.count()).select_from(ExerciseAttempt).where(ExerciseAttempt.user_id == user.user_id)) or 0
    seed = int(uuid.UUID(str(user.user_id)).int % 1_000_003) + attempts_count  # tất định theo trạng thái người học
    picked = choose_next(pool, weak_topics=weak, recent_errors=[d for d in recent_errors if d],
                         recent_exercise_ids=[str(e) for e in recent], topic=topic, exercise_type=exercise_type, seed=seed)
    if picked is None:
        raise AppError(404, "exercise_not_available", "Chưa có bài tập phù hợp với lựa chọn này.")
    return db.get(Exercise, uuid.UUID(picked.exercise_id))


def _placement_weak_topics(db: Session, user: User, lang: str) -> list[str]:
    latest = db.scalar(select(PlacementResult).where(PlacementResult.user_id == user.user_id, PlacementResult.language_code == lang,
                                                     PlacementResult.status == "completed").order_by(PlacementResult.completed_at.desc()).limit(1))
    missed = {t.lower() for t in ((latest.answer_summary or {}).get("missed_topics", []) if latest else [])}
    if not missed:
        return []
    try:
        return [x.document_id for x in load_lessons(lang) if x.topic.lower() in missed]
    except Exception:
        return []


# ---------- Nộp bài và chấm ----------


def _enforce_submit_limits(db: Session, user: User, limits: AppLimits | None, settings) -> None:
    if limits is None:
        return
    key = str(user.user_id)
    minute = limits.exercise_submit_minute.check(key)
    if not minute.allowed:
        log_rejection("exercise_minute", user_id=user.user_id, retry_after=minute.retry_after)
        raise rate_limit_error(429, "exercise_rate_limited", "Bạn nộp bài hơi nhanh. Vui lòng đợi một chút.", minute.retry_after)
    if settings.exercise_submit_per_day:
        start, end = local_day_bounds(limits_module.utcnow(), settings.user_timezone)
        today = db.scalar(select(func.count()).select_from(ExerciseAttempt).where(
            ExerciseAttempt.user_id == user.user_id, ExerciseAttempt.created_at >= start, ExerciseAttempt.created_at < end)) or 0
        if today >= settings.exercise_submit_per_day:
            wait = seconds_until_local_midnight(limits_module.utcnow(), settings.user_timezone)
            raise rate_limit_error(429, "exercise_daily_limit_reached", "Bạn đã nộp đủ số bài hôm nay. Hãy quay lại vào ngày mai.", wait)
    limits.exercise_submit_minute.record(key)


def _check_llm_capacity(llm: LLMService, limits: AppLimits | None, attempt_id: uuid.UUID) -> None:
    """Chấm bằng LLM dùng chung tạm khóa và ngưỡng phút toàn hệ thống với chat (khi gọi LLM thật)."""
    if limits is None or not getattr(llm, "consumes_quota", True):
        return
    details = [{"attempt_id": str(attempt_id)}]
    cooldown = limits.llm_cooldown.remaining()
    if cooldown > 0:
        raise AppError(429, "service_busy", SERVICE_BUSY, headers={"Retry-After": str(max(1, round(cooldown)))}, details=details)
    decision = limits.llm_global_minute.hit("llm")
    if not decision.allowed:
        raise AppError(429, "service_busy", SERVICE_BUSY, headers={"Retry-After": str(max(1, round(decision.retry_after)))}, details=details)


def build_grader_request(ex_type: str, payload: dict, key: dict, level_code: str, answer: str, language_code: str) -> LLMRequest:
    config = get_language_config(language_code)
    task = payload.get("source_vi") or payload.get("sentence") or ""
    reference = key.get("reference") or " | ".join(key.get("accepted", []))
    prompt = render_prompt(language_code, "grader", level_code=level_code, exercise_type=ex_type,
                           task=task.replace("<<<", "").replace(">>>", ""), reference=reference,
                           rubric="; ".join(key.get("rubric", [])) or "Correct the single error; keep the meaning.",
                           error_types=", ".join(config.error_type_ids),
                           answer=clean_answer(answer))  # template đặt bài làm giữa <<<BAI_LAM>>> … <<<HET_BAI_LAM>>>
    return LLMRequest(system_prompt=prompt, messages=(ChatMessage("user", "Grade the answer."),),
                      response_schema=GraderOutput, max_output_tokens=1024)


def _record_errors(db: Session, attempt: ExerciseAttempt, ex: Exercise, error_types: list[str]) -> None:
    for et in error_types:
        db.add(ErrorEvent(user_id=attempt.user_id, language_code=ex.language_code, error_type=et, document_id=ex.document_id,
                          exercise_id=ex.exercise_id, attempt_id=attempt.attempt_id))


def _apply_llm_grade(db: Session, attempt: ExerciseAttempt, ex: Exercise, grade: LlmGrade) -> None:
    attempt.grading_status, attempt.graded_by = "graded", "llm"
    attempt.score = grade.score
    attempt.is_correct = grade.verdict == "correct"
    types = sorted({e["error_type"] for e in grade.errors}) or ([] if attempt.is_correct else [ex.error_type])
    attempt.error_types = types
    attempt.feedback = {"verdict": grade.verdict, "errors": grade.errors, "feedback_vi": grade.feedback_vi}
    if not attempt.is_correct:
        _record_errors(db, attempt, ex, types)


def submit_attempt(db: Session, llm: LLMService | None, user: User, exercise_id: uuid.UUID, answer: dict,
                   limits: AppLimits | None = None) -> tuple[ExerciseAttempt, Exercise]:
    settings = get_settings()
    ex = get_exercise(db, user, exercise_id)
    _enforce_submit_limits(db, user, limits, settings)
    config = get_language_config(ex.language_code)
    started = time.perf_counter()
    outcome = grade_rule(ex.exercise_type, ex.prompt_payload, ex.answer_key, answer, config)
    attempt = ExerciseAttempt(user_id=user.user_id, exercise_id=ex.exercise_id, language_code=ex.language_code, answer=answer)
    if not outcome.needs_llm:
        attempt.grading_status, attempt.graded_by = "graded", "rule"
        attempt.is_correct, attempt.score = outcome.is_correct, outcome.score
        attempt.error_types = [] if outcome.is_correct else [ex.error_type]
        attempt.feedback = {"verdict": "correct" if outcome.is_correct else "incorrect"}
        attempt.latency_ms = int((time.perf_counter() - started) * 1000)
        db.add(attempt)
        db.flush()
        if not outcome.is_correct:
            _record_errors(db, attempt, ex, [ex.error_type])
        db.commit()
        logger.info("exercise graded attempt=%s type=%s by=rule correct=%s", attempt.attempt_id, ex.exercise_type, outcome.is_correct)
        return attempt, ex
    # Cần LLM: lưu bài làm TRƯỚC (không mất bài nếu LLM lỗi), commit, rồi gọi LLM khi không có giao dịch mở.
    attempt.grading_status, attempt.graded_by = "pending", "pending"
    db.add(attempt)
    db.commit()
    return _grade_pending_with_llm(db, llm, attempt.attempt_id, limits)


def _grade_pending_with_llm(db: Session, llm: LLMService | None, attempt_id: uuid.UUID, limits: AppLimits | None):
    attempt = db.get(ExerciseAttempt, attempt_id)
    ex = db.get(Exercise, attempt.exercise_id)
    # Đọc mọi giá trị cần dùng rồi kết thúc giao dịch đọc trước khi gọi LLM.
    ex_type, payload, key, level, lang = ex.exercise_type, dict(ex.prompt_payload), dict(ex.answer_key), ex.level_code, ex.language_code
    answer = (attempt.answer or {}).get("text", "") if isinstance(attempt.answer, dict) else ""
    db.commit()
    details = [{"attempt_id": str(attempt_id)}]
    if llm is None:
        raise AppError(503, "llm_not_configured", "Gia sư AI chưa được cấu hình; bài làm đã được lưu để chấm sau.", details=details)
    _check_llm_capacity(llm, limits, attempt_id)
    started = time.perf_counter()
    try:
        result = llm.generate(build_grader_request(ex_type, payload, key, level, answer, lang))
        grade = finalize_llm_grade(result.parsed, get_language_config(lang))
    except LLMError as error:
        logger.warning("exercise llm_grade_error attempt=%s code=%s", attempt_id, error.code)
        from app.services.chat import llm_error_to_app_error

        app_error = llm_error_to_app_error(error)
        app_error.details = details
        app_error.message = f"{app_error.message} Bài làm đã được lưu, bạn có thể chấm lại sau."
        raise app_error from None
    attempt = db.get(ExerciseAttempt, attempt_id)
    ex = db.get(Exercise, attempt.exercise_id)
    if attempt.grading_status == "graded":  # đã được chấm ở yêu cầu khác (idempotent)
        return attempt, ex
    _apply_llm_grade(db, attempt, ex, grade)
    attempt.latency_ms = int((time.perf_counter() - started) * 1000)
    db.commit()
    logger.info("exercise graded attempt=%s type=%s by=llm verdict=%s", attempt_id, ex_type, grade.verdict)
    return attempt, ex


def get_own_attempt(db: Session, user: User, attempt_id: uuid.UUID) -> ExerciseAttempt:
    attempt = db.scalar(select(ExerciseAttempt).where(ExerciseAttempt.attempt_id == attempt_id, ExerciseAttempt.user_id == user.user_id))
    if attempt is None:
        raise AppError(404, "exercise_attempt_not_found", "Không tìm thấy bài làm.")
    return attempt


def regrade(db: Session, llm: LLMService | None, user: User, attempt_id: uuid.UUID, limits: AppLimits | None = None):
    attempt = get_own_attempt(db, user, attempt_id)
    if attempt.grading_status == "graded":  # idempotent: không chấm lại, không tốn lượt
        return attempt, db.get(Exercise, attempt.exercise_id)
    if limits is not None:
        minute = limits.exercise_submit_minute.hit(str(user.user_id))
        if not minute.allowed:
            raise rate_limit_error(429, "exercise_rate_limited", "Bạn thao tác hơi nhanh. Vui lòng đợi một chút.", minute.retry_after)
    return _grade_pending_with_llm(db, llm, attempt.attempt_id, limits)


def history(db: Session, user: User, limit: int = 50) -> list[tuple[ExerciseAttempt, Exercise]]:
    rows = db.execute(select(ExerciseAttempt, Exercise).join(Exercise, Exercise.exercise_id == ExerciseAttempt.exercise_id)
                      .where(ExerciseAttempt.user_id == user.user_id).order_by(ExerciseAttempt.created_at.desc()).limit(limit)).all()
    return [(a, e) for a, e in rows]


def error_summary(db: Session, user: User) -> dict:
    since = limits_module.utcnow() - timedelta(days=30)
    attempts = db.execute(select(ExerciseAttempt.exercise_id, Exercise.document_id, Exercise.exercise_type, ExerciseAttempt.is_correct,
                                 ExerciseAttempt.created_at).join(Exercise, Exercise.exercise_id == ExerciseAttempt.exercise_id)
                          .where(ExerciseAttempt.user_id == user.user_id, ExerciseAttempt.created_at >= since)).all()
    errors = db.execute(select(ErrorEvent.error_type, ErrorEvent.document_id, ErrorEvent.created_at)
                        .where(ErrorEvent.user_id == user.user_id, ErrorEvent.created_at >= since)).all()
    return summarize([AttemptFact(str(a[0]), a[1], a[2], a[3], a[4]) for a in attempts],
                     [ErrorFact(e[0], e[1], e[2]) for e in errors], limits_module.utcnow(), get_settings().user_timezone)


# ---------- Duyệt bài (chỉ khi EXERCISE_ADMIN_ENABLED) ----------


def require_admin() -> None:
    if not get_settings().exercise_admin_enabled:
        raise AppError(404, "not_found", "Không tìm thấy tài nguyên.")


def review_queue(db: Session, status: str | None, limit: int = 50) -> list[Exercise]:
    query = select(Exercise).order_by(Exercise.created_at)
    if status:
        query = query.where(Exercise.review_status == status)
    return list(db.scalars(query.limit(limit)))


def review(db: Session, exercise_id: uuid.UUID, decision: str, reviewer: str, edits: dict | None) -> Exercise:
    ex = db.get(Exercise, exercise_id)
    if ex is None:
        raise AppError(404, "exercise_not_found", "Không tìm thấy bài tập.")
    if decision == "edit" and edits:
        ex.prompt_payload = edits.get("prompt", ex.prompt_payload)
        ex.answer_key = edits.get("answer_key", ex.answer_key)
        ex.explanation = edits.get("explanation", ex.explanation)
        ex.review_status = "approved"
    else:
        ex.review_status = "approved" if decision == "approve" else "rejected_by_human"
    ex.reviewer, ex.reviewed_at = reviewer[:120], datetime.now(timezone.utc)
    db.commit()
    return ex
