"""Bài tập, lượt làm bài, sự kiện lỗi (Tuần 5B). Mọi bảng có language_code. answer_key CHỈ dùng phía máy chủ."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

CODE = 16


class Exercise(Base):
    __tablename__ = "exercises"
    __table_args__ = (
        UniqueConstraint("language_code", "content_hash", name="uq_exercises_language_content_hash"),
        CheckConstraint("validation_status IN ('draft', 'validated', 'rejected')", name="validation_status_valid"),
        CheckConstraint("review_status IN ('unreviewed', 'approved', 'rejected_by_human')", name="review_status_valid"),
        Index("ix_exercises_pick", "language_code", "validation_status", "document_id", "exercise_type"),
    )

    exercise_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    language_code: Mapped[str] = mapped_column(String(CODE))
    level_code: Mapped[str] = mapped_column(String(CODE))
    exercise_type: Mapped[str] = mapped_column(String(32))
    document_id: Mapped[str] = mapped_column(String(80))
    source_document_ids: Mapped[Any] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    topic: Mapped[str] = mapped_column(String(120))
    error_type: Mapped[str] = mapped_column(String(64))
    prompt_payload: Mapped[Any] = mapped_column(JSONB)
    answer_key: Mapped[Any] = mapped_column(JSONB)  # KHÔNG BAO GIỜ trả trước khi nộp
    explanation: Mapped[str] = mapped_column(Text, server_default="")
    generation_meta: Mapped[Any] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    content_hash: Mapped[str] = mapped_column(String(64))
    validation_status: Mapped[str] = mapped_column(String(16), server_default="draft")
    reject_reasons: Mapped[Any] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    review_status: Mapped[str] = mapped_column(String(24), server_default="unreviewed")
    reviewer: Mapped[str | None] = mapped_column(String(120))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())

    def __repr__(self) -> str:
        return f"Exercise(exercise_id={self.exercise_id}, type={self.exercise_type!r})"


class ExerciseAttempt(Base):
    __tablename__ = "exercise_attempts"
    __table_args__ = (
        CheckConstraint("graded_by IN ('rule', 'llm', 'pending')", name="graded_by_valid"),
        CheckConstraint("grading_status IN ('graded', 'pending')", name="grading_status_valid"),
        Index("ix_exercise_attempts_user_created", "user_id", "created_at"),
    )

    attempt_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id", ondelete="RESTRICT"))
    exercise_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exercises.exercise_id", ondelete="RESTRICT"))
    language_code: Mapped[str] = mapped_column(String(CODE))
    answer: Mapped[Any] = mapped_column(JSONB)
    is_correct: Mapped[bool | None] = mapped_column(Boolean)
    score: Mapped[float | None] = mapped_column(Float)
    graded_by: Mapped[str] = mapped_column(String(16), server_default="pending")
    grading_status: Mapped[str] = mapped_column(String(16), server_default="pending")
    feedback: Mapped[Any] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    error_types: Mapped[Any] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())

    def __repr__(self) -> str:  # không in câu trả lời
        return f"ExerciseAttempt(attempt_id={self.attempt_id}, status={self.grading_status!r})"


class ErrorEvent(Base):
    __tablename__ = "error_events"
    __table_args__ = (Index("ix_error_events_user_created", "user_id", "created_at"),)

    event_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id", ondelete="RESTRICT"))
    language_code: Mapped[str] = mapped_column(String(CODE))
    error_type: Mapped[str] = mapped_column(String(64))
    document_id: Mapped[str | None] = mapped_column(String(80))
    exercise_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("exercises.exercise_id", ondelete="RESTRICT"))
    attempt_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("exercise_attempts.attempt_id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())
