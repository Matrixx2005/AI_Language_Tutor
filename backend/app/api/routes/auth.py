from typing import Annotated

from fastapi import APIRouter, Body, status

from app.api.deps import DbSession
from app.core.security import create_access_token
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.profile import ProfileRead
from app.services import auth as auth_service
from app.services.profile import to_profile_read

router = APIRouter(prefix="/auth", tags=["auth"])

# Ví dụ hợp lệ hiển thị sẵn trên /docs (mẫu tự sinh "string" không qua được kiểm tra).
REGISTER_EXAMPLES = {
    "day_du": {
        "summary": "Đăng ký có tên hiển thị",
        "value": {"email": "minh@example.com", "password": "matkhau123", "display_name": "Minh"},
    },
    "toi_thieu": {
        "summary": "Chỉ email và mật khẩu",
        "value": {"email": "lan@example.com", "password": "matkhau123"},
    },
}
LOGIN_EXAMPLES = {
    "dang_nhap": {
        "summary": "Đăng nhập tài khoản ví dụ",
        "value": {"email": "minh@example.com", "password": "matkhau123"},
    },
}


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=ProfileRead)
def register(
    data: Annotated[RegisterRequest, Body(openapi_examples=REGISTER_EXAMPLES)],
    session: DbSession,
) -> ProfileRead:
    """Tạo tài khoản và hồ sơ học tập. Mật khẩu 8–128 ký tự, không trùng email.

    Không trả token: đăng nhập riêng ở `/auth/login`.
    """
    return to_profile_read(auth_service.register_user(session, data))


@router.post("/login", response_model=TokenResponse)
def login(
    data: Annotated[LoginRequest, Body(openapi_examples=LOGIN_EXAMPLES)],
    session: DbSession,
) -> TokenResponse:
    """Trả `access_token`. Trên /docs: copy token, bấm **Authorize** rồi dán vào."""
    user = auth_service.authenticate(session, data)
    token, expires_in = create_access_token(user.user_id)
    return TokenResponse(access_token=token, expires_in=expires_in)
