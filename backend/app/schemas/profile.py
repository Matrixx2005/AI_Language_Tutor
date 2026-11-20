from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator

from app.schemas.auth import DisplayName

LEARNING_GOAL_MAX_LENGTH = 1000
LearningGoal = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=LEARNING_GOAL_MAX_LENGTH)
]
LevelCode = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=16)]


class ProfileRead(BaseModel):
    """Hồ sơ của chính người dùng (gộp thông tin tài khoản cần hiển thị)."""

    user_id: uuid.UUID
    email: str
    display_name: str | None
    language_code: str
    current_level_code: str
    native_language_code: str
    learning_goal: str | None
    created_at: datetime
    updated_at: datetime


class ProfileUpdate(BaseModel):
    """PATCH: chỉ trường được gửi mới được cập nhật. Gửi null để xóa display_name/learning_goal.

    Không cho sửa email, language_code, native_language_code ở Tuần 2 (extra="forbid").
    Trình độ hợp lệ được kiểm tra theo languages/<language_code>.yaml ở tầng service.
    """

    model_config = ConfigDict(extra="forbid")

    display_name: DisplayName | None = None
    learning_goal: LearningGoal | None = None
    current_level_code: LevelCode | None = None

    @field_validator("current_level_code")
    @classmethod
    def _level_not_null(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Trình độ hiện tại không được để trống")
        return value
