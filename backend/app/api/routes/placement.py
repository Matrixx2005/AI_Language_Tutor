import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Response, status

from app.api.deps import CurrentUser, DbSession
from app.core.languages import get_language_config
from app.models import PlacementResult, Question
from app.schemas.placement import (
    GroupRead,
    PlacementAttemptRead,
    PlacementAttemptSummary,
    PlacementOutcomeRead,
    PlacementQuestionRead,
    PlacementSubmit,
    ReviewItem,
)
from app.schemas.profile import ProfileRead
from app.services import placement as placement_service
from app.services.profile import to_profile_read

# Mọi route lọc theo người dùng hiện tại; lượt của người khác → 404. Không dùng LLM.
router = APIRouter(prefix="/placement", tags=["placement"])


def _questions(questions: list[Question]) -> list[PlacementQuestionRead]:
    # CHỈ các trường an toàn: không correct_answer, không explanation, không level/topic.
    return [
        PlacementQuestionRead(
            question_id=q.question_id, position=i + 1, category=q.category, prompt=q.prompt, options=list(q.options)
        )
        for i, q in enumerate(questions)
    ]


def _outcome(attempt: PlacementResult, questions: list[Question]) -> PlacementOutcomeRead:
    summary = attempt.answer_summary or {}
    language = get_language_config(attempt.language_code)
    level = next((lv for lv in language.levels if lv.code == attempt.level_code), None)
    answers = {a["question_id"]: a for a in summary.get("answers", [])}
    groups = [GroupRead(**g) for g in summary.get("groups", [])]
    return PlacementOutcomeRead(
        score=int(attempt.score),
        max_score=int(attempt.max_score),
        percent=summary.get("percent", 0.0),
        suggested_level_code=attempt.level_code,
        suggested_level_name_vi=level.display_name_vi if level else attempt.level_code,
        groups=groups,
        weak_groups=[g for g in groups if g.weak],
        missed_topics=summary.get("missed_topics", []),
        review=[
            ReviewItem(
                question_id=q.question_id,
                prompt=q.prompt,
                options=list(q.options),
                selected=answers.get(str(q.question_id), {}).get("selected"),
                correct_answer=q.correct_answer,
                is_correct=answers.get(str(q.question_id), {}).get("is_correct", False),
                explanation=q.explanation,
            )
            for q in questions
        ],
        applied_at=attempt.applied_at,
        disclaimer=placement_service.disclaimer(language),
    )


def _attempt_read(attempt: PlacementResult, questions: list[Question]) -> PlacementAttemptRead:
    completed = attempt.status == placement_service.COMPLETED
    return PlacementAttemptRead(
        attempt_id=attempt.result_id,
        status=attempt.status,
        language_code=attempt.language_code,
        started_at=attempt.started_at,
        completed_at=attempt.completed_at,
        questions=None if completed else _questions(questions),
        result=_outcome(attempt, questions) if completed else None,
    )


@router.post("/attempts", response_model=PlacementAttemptRead, status_code=status.HTTP_201_CREATED)
def start_attempt(user: CurrentUser, db: DbSession, response: Response) -> PlacementAttemptRead:
    """Bắt đầu bài kiểm tra đầu vào (câu hỏi KHÔNG kèm đáp án). Đang có lượt dở → trả lại lượt đó (200)."""
    attempt, questions, created = placement_service.start_attempt(db, user)
    if not created:
        response.status_code = status.HTTP_200_OK
    return _attempt_read(attempt, questions)


@router.get("/attempts", response_model=list[PlacementAttemptSummary])
def list_attempts(user: CurrentUser, db: DbSession) -> list[PlacementAttemptSummary]:
    """20 lượt gần nhất của chính mình."""
    return [
        PlacementAttemptSummary(
            attempt_id=a.result_id, status=a.status, language_code=a.language_code, started_at=a.started_at,
            completed_at=a.completed_at, suggested_level_code=a.level_code,
            score=int(a.score) if a.score is not None else None,
            max_score=int(a.max_score) if a.max_score is not None else None,
            applied_at=a.applied_at,
        )
        for a in placement_service.list_attempts(db, user)
    ]


@router.get("/attempts/{attempt_id}", response_model=PlacementAttemptRead)
def get_attempt(attempt_id: uuid.UUID, user: CurrentUser, db: DbSession) -> PlacementAttemptRead:
    """Đang làm: câu hỏi (không đáp án). Đã nộp: kết quả, nhóm yếu, đáp án và giải thích."""
    return _attempt_read(*placement_service.get_attempt(db, user, attempt_id))


@router.post("/attempts/{attempt_id}/submit", response_model=PlacementAttemptRead)
def submit_attempt(
    attempt_id: uuid.UUID, data: Annotated[PlacementSubmit, Body()], user: CurrentUser, db: DbSession
) -> PlacementAttemptRead:
    """Nộp bài một lần duy nhất (lần hai → 409). Câu bỏ trống tính sai."""
    return _attempt_read(*placement_service.submit_attempt(db, user, attempt_id, data.answers))


@router.post("/attempts/{attempt_id}/apply", response_model=ProfileRead)
def apply_suggested_level(attempt_id: uuid.UUID, user: CurrentUser, db: DbSession) -> ProfileRead:
    """Người dùng xác nhận dùng trình độ đề xuất → cập nhật hồ sơ."""
    return to_profile_read(placement_service.apply_suggested_level(db, user, attempt_id))
