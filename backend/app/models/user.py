from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.learner_profile import LearnerProfile


class User(Base):
    """Tài khoản. Không chứa trình độ hay ngôn ngữ học (nằm ở learner_profiles)."""

    __tablename__ = "users"
    __table_args__ = (
        # Email phải được chuẩn hóa (bỏ khoảng trắng, chữ thường) trước khi lưu;
        # DB chặn thêm một lớp để unique không bị lách bằng chữ hoa.
        CheckConstraint("email = lower(btrim(email))", name="email_normalized"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    profile: Mapped[LearnerProfile | None] = relationship(back_populates="user")

    def __repr__(self) -> str:  # không in email/hash vào log
        return f"User(user_id={self.user_id})"
