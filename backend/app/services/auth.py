"""Nghiệp vụ đăng ký/đăng nhập. Không log email hay mật khẩu."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.languages import get_language_config
from app.core.security import burn_password_check, hash_password, verify_password
from app.models import LearnerProfile, User
from app.schemas.auth import LoginRequest, RegisterRequest


# Tạo lỗi mới mỗi lần raise (không dùng chung instance giữa các request).
def email_taken() -> AppError:
    return AppError(409, "email_already_registered", "Email này đã được đăng ký.")


def invalid_credentials() -> AppError:
    return AppError(401, "invalid_credentials", "Email hoặc mật khẩu không đúng.")


def register_user(session: Session, data: RegisterRequest) -> User:
    if session.scalar(select(User.user_id).where(User.email == data.email)) is not None:
        raise email_taken()

    language = get_language_config(get_settings().default_language_code)
    user = User(
        email=data.email,
        password_hash=hash_password(data.password.get_secret_value()),
        display_name=data.display_name,
    )
    # Trình độ ban đầu lấy từ cấu hình ngôn ngữ, không dựa vào default 'A1' trong DB.
    user.profile = LearnerProfile(
        language_code=language.language_code,
        current_level_code=language.default_level_code,
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError as exc:
        # Hai request đăng ký cùng email gần như đồng thời: unique constraint là lớp chặn cuối.
        session.rollback()
        if "uq_users_email" in str(exc.orig):
            raise email_taken() from None
        raise
    session.refresh(user)
    return user


def authenticate(session: Session, data: LoginRequest) -> User:
    password = data.password.get_secret_value()
    user = session.scalar(select(User).where(User.email == data.email))
    if user is None:
        burn_password_check(password)  # thời gian phản hồi như khi sai mật khẩu
        raise invalid_credentials()

    is_valid, upgraded_hash = verify_password(password, user.password_hash)
    if not is_valid:
        raise invalid_credentials()
    if upgraded_hash is not None:
        user.password_hash = upgraded_hash  # tham số Argon2 đã được nâng: băm lại
        session.commit()
    return user
