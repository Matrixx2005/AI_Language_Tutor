"""Bài tập (Tuần 5B). Owner check → 404; không bao giờ trả answer_key trước khi nộp; lỗi theo mã ổn định."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status

from app.api.deps import CurrentUser, DbSession, Limits
from app.llm import get_llm_service
from app.llm.errors import LLMConfigError
from app.llm.service import LLMService
from app.schemas.exercise import AdminExerciseRead, AttemptCreate, AttemptRead, ExerciseRead, ReviewIn
from app.services import exercises as service

router = APIRouter(tags=["exercises"])


def get_grader_llm() -> LLMService | None:
    """LLM để chấm bài dạng mở. Thiếu cấu hình → None: bài làm vẫn được lưu 'pending' (không mất)."""
    try:
        return get_llm_service()
    except LLMConfigError:
        return None


GraderLLM = Annotated[LLMService | None, Depends(get_grader_llm)]


@router.get("/exercises/next", response_model=ExerciseRead)
def next_exercise(user: CurrentUser, db: DbSession, topic: Annotated[str | None, Query(max_length=80)] = None,
                  type: Annotated[str | None, Query(max_length=32)] = None) -> ExerciseRead:  # noqa: A002
    """Bài tiếp theo: ưu tiên chủ đề có lỗi gần đây, rồi chủ đề yếu từ placement; tránh bài vừa làm."""
    return ExerciseRead(**service.public_exercise(service.next_exercise(db, user, topic, type)))


@router.get("/exercises/history", response_model=list[AttemptRead])
def history(user: CurrentUser, db: DbSession) -> list[AttemptRead]:
    return [AttemptRead(**service.attempt_view(a, e)) for a, e in service.history(db, user)]


@router.get("/exercises/{exercise_id}", response_model=ExerciseRead)
def get_exercise(exercise_id: uuid.UUID, user: CurrentUser, db: DbSession) -> ExerciseRead:
    return ExerciseRead(**service.public_exercise(service.get_exercise(db, user, exercise_id)))


@router.post("/exercises/{exercise_id}/attempts", response_model=AttemptRead, status_code=status.HTTP_201_CREATED)
def submit(exercise_id: uuid.UUID, data: Annotated[AttemptCreate, Body()], user: CurrentUser, db: DbSession,
           limits: Limits, llm: GraderLLM) -> AttemptRead:
    """Nộp bài. mcq/cloze/reorder chấm bằng quy tắc. Bài cần AI chấm mà AI lỗi: bài làm vẫn được lưu (pending),
    API trả mã lỗi ổn định kèm details.attempt_id để gọi POST /exercises/attempts/{attempt_id}/regrade."""
    attempt, ex = service.submit_attempt(db, llm, user, exercise_id, data.answer.model_dump(), limits)
    return AttemptRead(**service.attempt_view(attempt, ex))


@router.post("/exercises/attempts/{attempt_id}/regrade", response_model=AttemptRead)
def regrade(attempt_id: uuid.UUID, user: CurrentUser, db: DbSession, limits: Limits, llm: GraderLLM) -> AttemptRead:
    """Chấm lại bài 'pending'. Đã chấm thì trả nguyên kết quả (idempotent, không tốn lượt)."""
    attempt, ex = service.regrade(db, llm, user, attempt_id, limits)
    return AttemptRead(**service.attempt_view(attempt, ex))


@router.get("/errors/summary")
def error_summary(user: CurrentUser, db: DbSession) -> dict:
    """Tổng hợp 30 ngày: loại lỗi hay gặp, độ chính xác theo chủ đề/dạng, xu hướng 7/30 ngày, chủ đề nên luyện."""
    return service.error_summary(db, user)


@router.get("/exercises/admin/queue", response_model=list[AdminExerciseRead], include_in_schema=False)
def admin_queue(user: CurrentUser, db: DbSession, review_status: Annotated[str | None, Query(max_length=24)] = None) -> list[AdminExerciseRead]:
    service.require_admin()
    return [AdminExerciseRead.model_validate(e) for e in service.review_queue(db, review_status)]


@router.post("/exercises/admin/{exercise_id}/review", response_model=AdminExerciseRead, include_in_schema=False)
def admin_review(exercise_id: uuid.UUID, data: Annotated[ReviewIn, Body()], user: CurrentUser, db: DbSession) -> AdminExerciseRead:
    service.require_admin()
    return AdminExerciseRead.model_validate(service.review(db, exercise_id, data.decision, data.reviewer, data.edits))
