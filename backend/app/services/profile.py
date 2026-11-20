from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.languages import get_language_config
from app.models import User
from app.schemas.profile import ProfileRead, ProfileUpdate


def _profile_of(user: User):
    if user.profile is None:  # không xảy ra với tài khoản tạo qua API (đăng ký tạo cả hồ sơ)
        raise AppError(404, "profile_not_found", "Không tìm thấy hồ sơ học tập.")
    return user.profile


def to_profile_read(user: User) -> ProfileRead:
    profile = _profile_of(user)
    return ProfileRead(
        user_id=user.user_id,
        email=user.email,
        display_name=user.display_name,
        language_code=profile.language_code,
        current_level_code=profile.current_level_code,
        native_language_code=profile.native_language_code,
        learning_goal=profile.learning_goal,
        created_at=user.created_at,
        updated_at=max(user.updated_at, profile.updated_at),
    )


def update_profile(session: Session, user: User, data: ProfileUpdate) -> ProfileRead:
    profile = _profile_of(user)
    changes = data.model_dump(exclude_unset=True)  # PATCH: chỉ trường được gửi

    if "current_level_code" in changes:
        language = get_language_config(profile.language_code)
        if not language.is_valid_level(changes["current_level_code"]):
            raise AppError(
                422,
                "invalid_level_code",
                f"Trình độ không hợp lệ. Chọn một trong: {', '.join(language.level_codes)}.",
            )
        profile.current_level_code = changes["current_level_code"]
    if "display_name" in changes:
        user.display_name = changes["display_name"]
    if "learning_goal" in changes:
        profile.learning_goal = changes["learning_goal"]

    session.commit()
    session.refresh(user)
    session.refresh(profile)
    return to_profile_read(user)
