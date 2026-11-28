from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ExerciseRead(BaseModel):
    """Bài tập TRƯỚC khi nộp: chỉ đề (prompt). Không có answer_key, explanation hay đáp án."""

    exercise_id: uuid.UUID
    language_code: str
    level_code: str
    exercise_type: str
    document_id: str
    topic: str
    prompt: dict[str, Any]
    review_status: str


class AnswerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=500)


class AttemptCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer: AnswerIn


class Solution(BaseModel):
    correct_answers: list[str]
    explanation: str
    source: dict[str, str]


class AttemptRead(BaseModel):
    """Kết quả SAU khi nộp: chấm điểm, phản hồi, đáp án + giải thích + bài học nguồn."""

    attempt_id: uuid.UUID
    exercise_id: uuid.UUID
    grading_status: str
    graded_by: str
    is_correct: bool | None
    score: float | None
    feedback: dict[str, Any]
    error_types: list[str]
    answer: dict[str, Any]
    created_at: datetime
    solution: Solution


class ReviewIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["approve", "reject", "edit"]
    reviewer: str = Field(min_length=1, max_length=120)
    edits: dict[str, Any] | None = None


class AdminExerciseRead(BaseModel):
    """Chỉ cho trang duyệt (EXERCISE_ADMIN_ENABLED=true): có đáp án và kết quả kiểm tra."""

    model_config = ConfigDict(from_attributes=True)
    exercise_id: uuid.UUID
    language_code: str
    level_code: str
    exercise_type: str
    document_id: str
    error_type: str
    prompt_payload: dict[str, Any]
    answer_key: dict[str, Any]
    explanation: str
    validation_status: str
    reject_reasons: list[Any]
    generation_meta: dict[str, Any]
    review_status: str
    reviewer: str | None
    reviewed_at: datetime | None
