from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User

# Mã ngôn ngữ/trình độ là chuỗi mở, không phải enum. Giá trị hợp lệ được kiểm tra ở tầng
# ứng dụng theo languages/<code>.yaml. Default dưới đây theo ERD đã duyệt.
CODE_LENGTH = 16


class LearnerProfile(Base):
    __tablename__ = "learner_profiles"

    # 1:1 với users. Không cascade khi xóa user: chính sách xóa tài khoản chưa được chốt
    # (docs/DATABASE_DESIGN.md), nên DB chặn xóa user còn hồ sơ thay vì âm thầm xóa dữ liệu.
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.user_id", ondelete="RESTRICT"), primary_key=True
    )
    language_code: Mapped[str] = mapped_column(String(CODE_LENGTH), server_default="en")
    current_level_code: Mapped[str] = mapped_column(String(CODE_LENGTH), server_default="A1")
    native_language_code: Mapped[str] = mapped_column(String(CODE_LENGTH), server_default="vi")
    learning_goal: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="profile")

    def __repr__(self) -> str:
        return f"LearnerProfile(user_id={self.user_id}, language_code={self.language_code!r})"
