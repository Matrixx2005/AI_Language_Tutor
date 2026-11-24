from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PlacementQuestionRead(BaseModel):
    """Câu hỏi khi đang làm bài: KHÔNG có đáp án đúng, giải thích, trình độ hay chủ đề."""

    question_id: uuid.UUID
    position: int
    category: str
    prompt: str
    options: list[str]


class GroupRead(BaseModel):
    level_code: str
    category: str
    correct: int
    total: int
    percent: float
    weak: bool


class ReviewItem(BaseModel):
    """Chỉ trả SAU khi nộp bài."""

    question_id: uuid.UUID
    prompt: str
    options: list[str]
    selected: str | None
    correct_answer: str
    is_correct: bool
    explanation: str | None


class PlacementOutcomeRead(BaseModel):
    score: int
    max_score: int
    percent: float
    suggested_level_code: str
    suggested_level_name_vi: str
    groups: list[GroupRead]
    weak_groups: list[GroupRead]
    missed_topics: list[str]
    review: list[ReviewItem]
    applied_at: datetime | None
    disclaimer: str


class PlacementAttemptRead(BaseModel):
    attempt_id: uuid.UUID
    status: str
    language_code: str
    started_at: datetime
    completed_at: datetime | None
    questions: list[PlacementQuestionRead] | None = Field(
        default=None, description="Chỉ có khi đang làm bài (không kèm đáp án)"
    )
    result: PlacementOutcomeRead | None = Field(default=None, description="Chỉ có sau khi nộp bài")


class PlacementAttemptSummary(BaseModel):
    attempt_id: uuid.UUID
    status: str
    language_code: str
    started_at: datetime
    completed_at: datetime | None
    suggested_level_code: str | None
    score: int | None
    max_score: int | None
    applied_at: datetime | None


class PlacementSubmit(BaseModel):
    """question_id → lựa chọn. Câu không có trong `answers`, hoặc giá trị null/"" = bỏ trống."""

    model_config = ConfigDict(extra="forbid")

    answers: dict[uuid.UUID, str | None] = Field(default_factory=dict, max_length=500)
