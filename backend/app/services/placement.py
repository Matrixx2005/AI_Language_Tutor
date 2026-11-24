"""Bài kiểm tra đầu vào (placement). Chấm HOÀN TOÀN phía máy chủ bằng đáp án đã duyệt; không dùng LLM.

- Bắt đầu: trả câu hỏi KHÔNG kèm đáp án; đang có lượt dở thì trả lại lượt đó (mỗi người một lượt
  đang làm cho mỗi ngôn ngữ — unique index trong DB là lớp chặn cuối).
- Nộp: khóa dòng (SELECT ... FOR UPDATE) → không nộp hai lần, kể cả hai request đồng thời.
- Kết quả chỉ là ĐỀ XUẤT; người dùng xác nhận thì mới cập nhật current_level_code (quyết định 2).
- Lượt của người khác → 404 (không xác nhận lượt đó tồn tại).
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.languages import LanguageConfig, UnknownLanguageError, get_language_config
from app.models import PlacementResult, Question, User
from app.services.placement_scoring import (
    PlacementAnswerError,
    ScoringQuestion,
    score_placement,
)

logger = logging.getLogger("app.placement")

IN_PROGRESS = "in_progress"
COMPLETED = "completed"
DISCLAIMER = "Kết quả chỉ mang tính tham khảo để chọn bài học phù hợp, không phải chứng chỉ CEFR chính thức."
PROVISIONAL_NOTE = " Ngưỡng xếp trình độ đang ở mức tạm thời, chưa được hiệu chuẩn trên người học thật."


def _not_found() -> AppError:
    return AppError(404, "placement_not_found", "Không tìm thấy bài kiểm tra.")


def _not_available() -> AppError:
    return AppError(422, "placement_not_available", "Chưa có bài kiểm tra đầu vào cho ngôn ngữ này.")


def _language_for(user: User) -> LanguageConfig:
    if user.profile is None:
        raise AppError(404, "profile_not_found", "Không tìm thấy hồ sơ học tập.")
    try:
        language = get_language_config(user.profile.language_code)
    except UnknownLanguageError:
        raise _not_available() from None
    if language.placement is None or not language.placement.question_set:
        raise _not_available()
    return language


def _questions_if_complete(db: Session, ids: list[str]) -> list[Question] | None:
    """Câu hỏi theo đúng thứ tự đề; None nếu có câu không còn trong bảng questions."""
    rows = {str(q.question_id): q for q in db.scalars(select(Question).where(Question.question_id.in_(ids)))}
    if len(rows) != len(ids):
        return None
    return [rows[qid] for qid in ids]


def _questions_in_order(db: Session, ids: list[str]) -> list[Question]:
    questions = _questions_if_complete(db, ids)
    if questions is None:
        raise AppError(409, "placement_questions_changed", "Bộ câu hỏi đã thay đổi. Vui lòng bắt đầu bài mới.")
    return questions


def _discard_stale_in_progress(db: Session, attempt: PlacementResult) -> None:
    """Xóa lượt ĐANG LÀM không còn khớp bộ câu hỏi (chưa có kết quả nên không mất dữ liệu học).
    Điều kiện status='in_progress' + user_id nằm ngay trong câu DELETE: không bao giờ xóa lượt đã nộp."""
    deleted = db.execute(
        delete(PlacementResult).where(
            PlacementResult.result_id == attempt.result_id,
            PlacementResult.user_id == attempt.user_id,
            PlacementResult.status == IN_PROGRESS,
        )
    ).rowcount
    db.expunge(attempt)
    db.flush()
    logger.info("placement stale_attempt_discarded attempt=%s deleted=%d", attempt.result_id, deleted)


def _own_attempt(db: Session, user: User, attempt_id: uuid.UUID, *, for_update: bool = False) -> PlacementResult:
    query = select(PlacementResult).where(
        PlacementResult.result_id == attempt_id, PlacementResult.user_id == user.user_id
    )
    if for_update:
        query = query.with_for_update()
    attempt = db.scalar(query)
    if attempt is None:
        raise _not_found()
    return attempt


def _in_progress(db: Session, user: User, language_code: str) -> PlacementResult | None:
    return db.scalar(
        select(PlacementResult).where(
            PlacementResult.user_id == user.user_id,
            PlacementResult.language_code == language_code,
            PlacementResult.status == IN_PROGRESS,
        )
    )


def start_attempt(db: Session, user: User) -> tuple[PlacementResult, list[Question], bool]:
    """Trả (lượt, câu hỏi theo thứ tự, có_tạo_mới)."""
    language = _language_for(user)
    existing = _in_progress(db, user, language.language_code)
    if existing is not None:
        current = _questions_if_complete(db, existing.question_ids)
        if current is not None:
            return existing, current, False
        # Bộ câu hỏi đã đổi (câu bị xóa/thay): bỏ lượt dở lỗi thời rồi tạo lượt mới bên dưới (201).
        _discard_stale_in_progress(db, existing)

    level_order = {code: index for index, (code, _) in enumerate(language.placement.thresholds)}
    questions = sorted(
        db.scalars(
            select(Question).where(
                Question.question_set == language.placement.question_set,
                Question.language_code == language.language_code,
            )
        ),
        key=lambda q: (level_order.get(q.level_code, len(level_order)), q.external_id),
    )
    if not questions:
        raise _not_available()
    attempt = PlacementResult(
        user_id=user.user_id,
        language_code=language.language_code,
        question_set=language.placement.question_set,
        status=IN_PROGRESS,
        question_ids=[str(q.question_id) for q in questions],
    )
    db.add(attempt)
    try:
        db.commit()
    except IntegrityError:  # request song song vừa tạo lượt đang làm: dùng lượt đó
        db.rollback()
        existing = _in_progress(db, user, language.language_code)
        if existing is None:
            raise
        return existing, _questions_in_order(db, existing.question_ids), False
    db.refresh(attempt)
    logger.info("placement start attempt=%s questions=%d", attempt.result_id, len(questions))
    return attempt, questions, True


def get_attempt(db: Session, user: User, attempt_id: uuid.UUID) -> tuple[PlacementResult, list[Question]]:
    attempt = _own_attempt(db, user, attempt_id)
    return attempt, _questions_in_order(db, attempt.question_ids)


def list_attempts(db: Session, user: User, limit: int = 20) -> list[PlacementResult]:
    return list(
        db.scalars(
            select(PlacementResult)
            .where(PlacementResult.user_id == user.user_id)
            .order_by(PlacementResult.started_at.desc())
            .limit(limit)
        )
    )


def submit_attempt(
    db: Session, user: User, attempt_id: uuid.UUID, answers: dict[uuid.UUID, str | None]
) -> tuple[PlacementResult, list[Question]]:
    attempt = _own_attempt(db, user, attempt_id, for_update=True)
    if attempt.status != IN_PROGRESS:
        db.rollback()
        raise AppError(409, "placement_already_submitted", "Bài kiểm tra này đã được nộp.")
    language = get_language_config(attempt.language_code)
    questions = _questions_in_order(db, attempt.question_ids)
    scoring = [
        ScoringQuestion(str(q.question_id), q.level_code, q.category, q.topic, tuple(q.options), q.correct_answer)
        for q in questions
    ]
    try:
        outcome = score_placement(scoring, {str(qid): value for qid, value in answers.items()}, language.placement)
    except PlacementAnswerError as error:
        db.rollback()  # nhả khóa dòng; lượt vẫn đang làm
        message = "Có câu hỏi không thuộc bài này." if error.code == "unknown_question" else "Có lựa chọn không hợp lệ."
        raise AppError(422, error.code, message) from None

    attempt.status = COMPLETED
    attempt.completed_at = func.clock_timestamp()
    attempt.level_code = outcome.level_code
    attempt.score = outcome.correct
    attempt.max_score = outcome.total
    attempt.answer_summary = {
        "percent": outcome.percent,
        "answers": [
            {"question_id": r.question_id, "selected": r.selected, "is_correct": r.is_correct}
            for r in outcome.results
        ],
        "groups": [
            {"level_code": g.level_code, "category": g.category, "correct": g.correct,
             "total": g.total, "percent": g.percent, "weak": g.weak}
            for g in outcome.groups
        ],
        "missed_topics": list(outcome.missed_topics),
        "thresholds": [[code, value] for code, value in language.placement.thresholds],
        "thresholds_status": language.placement.status,
    }
    db.commit()
    db.refresh(attempt)
    logger.info(
        "placement submit attempt=%s score=%d/%d level=%s weak_groups=%d",
        attempt.result_id, outcome.correct, outcome.total, outcome.level_code, len(outcome.weak_groups),
    )
    return attempt, questions


def apply_suggested_level(db: Session, user: User, attempt_id: uuid.UUID) -> User:
    """Người dùng XÁC NHẬN dùng trình độ đề xuất → cập nhật hồ sơ. Chỉ lượt hoàn thành MỚI NHẤT của
    người dùng cho ngôn ngữ đó (lượt cũ → 409 placement_superseded). Gọi lại với lượt mới nhất không lỗi."""
    attempt = _own_attempt(db, user, attempt_id, for_update=True)
    if attempt.status != COMPLETED:
        db.rollback()
        raise AppError(409, "placement_not_completed", "Hãy nộp bài trước khi cập nhật trình độ.")
    latest_id = db.scalar(
        select(PlacementResult.result_id)
        .where(
            PlacementResult.user_id == user.user_id,
            PlacementResult.language_code == attempt.language_code,
            PlacementResult.status == COMPLETED,
        )
        .order_by(PlacementResult.completed_at.desc(), PlacementResult.started_at.desc())
        .limit(1)
    )
    if latest_id != attempt.result_id:
        db.rollback()
        raise AppError(409, "placement_superseded", "Đã có kết quả mới hơn. Hãy dùng kết quả bài làm gần nhất.")
    profile = user.profile
    language = get_language_config(attempt.language_code)
    if profile is None or profile.language_code != attempt.language_code or not language.is_valid_level(attempt.level_code):
        db.rollback()
        raise AppError(409, "placement_not_applicable", "Kết quả này không còn áp dụng cho hồ sơ hiện tại.")
    profile.current_level_code = attempt.level_code
    if attempt.applied_at is None:
        attempt.applied_at = func.clock_timestamp()
    db.commit()
    db.refresh(user)
    logger.info("placement apply attempt=%s level=%s", attempt.result_id, attempt.level_code)
    return user


def disclaimer(language: LanguageConfig) -> str:
    provisional = language.placement is not None and language.placement.status == "provisional"
    return DISCLAIMER + (PROVISIONAL_NOTE if provisional else "")
