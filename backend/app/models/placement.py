"""questions, placement_results theo ERD đã duyệt + bổ sung đã duyệt ở Tuần 3 (quyết định 7):
- questions: external_id (duy nhất), category, question_set; CHƯA có source_document_id (bảng
  documents chưa tồn tại — thêm ở tuần làm corpus).
- placement_results: status (in_progress/completed), started_at, question_ids, applied_at;
  completed_at/level_code/score/max_score/answer_summary được phép NULL khi đang làm.
FK RESTRICT: chính sách xóa dữ liệu chưa chốt.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

CODE_LENGTH = 16


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (
        Index("ix_questions_set_language_level_topic", "question_set", "language_code", "level_code", "topic"),
    )

    question_id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    external_id: Mapped[str] = mapped_column(String(64), unique=True)  # ID trong file nguồn
    question_set: Mapped[str] = mapped_column(String(64))  # ví dụ "placement_v1"
    language_code: Mapped[str] = mapped_column(String(CODE_LENGTH), server_default="en")
    level_code: Mapped[str] = mapped_column(String(CODE_LENGTH))
    category: Mapped[str] = mapped_column(String(32))
    topic: Mapped[str] = mapped_column(String(120))
    question_type: Mapped[str] = mapped_column(String(32), server_default="multiple_choice")
    prompt: Mapped[str] = mapped_column(Text)
    options: Mapped[Any] = mapped_column(JSONB)
    correct_answer: Mapped[Any] = mapped_column(JSONB)  # KHÔNG bao giờ trả cho client trước khi nộp
    explanation: Mapped[str | None] = mapped_column(Text)
    points: Mapped[float] = mapped_column(Numeric(6, 2), server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:  # không in đáp án
        return f"Question(external_id={self.external_id!r})"


class PlacementResult(Base):
    __tablename__ = "placement_results"
    __table_args__ = (
        CheckConstraint("status IN ('in_progress', 'completed')", name="status_valid"),
        CheckConstraint(
            "status = 'in_progress' OR (completed_at IS NOT NULL AND level_code IS NOT NULL "
            "AND score IS NOT NULL AND max_score IS NOT NULL)",
            name="completed_has_result",
        ),
        CheckConstraint("applied_at IS NULL OR status = 'completed'", name="applied_only_completed"),
        Index("ix_placement_results_user_id_started_at", "user_id", text("started_at DESC")),
        # Mỗi người chỉ có MỘT lượt đang làm cho mỗi ngôn ngữ (quyết định Tuần 3, mục 10).
        Index(
            "uq_placement_results_one_in_progress",
            "user_id", "language_code",
            unique=True,
            postgresql_where=text("status = 'in_progress'"),
        ),
    )

    result_id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id", ondelete="RESTRICT"))
    language_code: Mapped[str] = mapped_column(String(CODE_LENGTH), server_default="en")
    question_set: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), server_default="in_progress")
    question_ids: Mapped[Any] = mapped_column(JSONB)  # danh sách question_id (UUID dạng chuỗi), đúng thứ tự đề
    # clock_timestamp(): thời điểm thật (now() là lúc bắt đầu transaction → hai lượt cùng transaction trùng giờ).
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    level_code: Mapped[str | None] = mapped_column(String(CODE_LENGTH))  # trình độ ĐỀ XUẤT
    score: Mapped[float | None] = mapped_column(Numeric(6, 2))
    max_score: Mapped[float | None] = mapped_column(Numeric(6, 2))
    answer_summary: Mapped[Any | None] = mapped_column(JSONB)  # đáp án từng câu + nhóm yếu + chủ đề cần ôn
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # lúc người dùng xác nhận

    def __repr__(self) -> str:
        return f"PlacementResult(result_id={self.result_id}, status={self.status!r})"
