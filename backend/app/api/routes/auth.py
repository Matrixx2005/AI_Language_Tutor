from typing import Annotated

from fastapi import APIRouter, Body, Request, status

from app.api.deps import DbSession, Limits
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.limits import client_ip, log_rejection, rate_limit_error
from app.core.security import create_access_token
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, normalize_email
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


AUTH_LIMITED_MESSAGE = "Bạn đã thử quá nhiều lần. Vui lòng thử lại sau."


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=ProfileRead)
def register(
    data: Annotated[RegisterRequest, Body(openapi_examples=REGISTER_EXAMPLES)],
    request: Request,
    session: DbSession,
    limits: Limits,
) -> ProfileRead:
    """Tạo tài khoản và hồ sơ học tập. Mật khẩu 8–128 ký tự, không trùng email.

    Không trả token: đăng nhập riêng ở `/auth/login`. Giới hạn số lần đăng ký theo IP.
    """
    ip = client_ip(request, get_settings().trusted_proxy_count)
    decision = limits.register_ip.hit(f"register-ip:{ip}")
    if not decision.allowed:
        log_rejection("register_ip", ip=ip, retry_after=decision.retry_after)
        raise rate_limit_error(429, "auth_rate_limited", AUTH_LIMITED_MESSAGE, decision.retry_after)
    return to_profile_read(auth_service.register_user(session, data))


@router.post("/login", response_model=TokenResponse)
def login(
    data: Annotated[LoginRequest, Body(openapi_examples=LOGIN_EXAMPLES)],
    request: Request,
    session: DbSession,
    limits: Limits,
) -> TokenResponse:
    """Trả `access_token`. Trên /docs: copy token, bấm **Authorize** rồi dán vào.

    Đăng nhập SAI quá nhiều lần (theo email hoặc theo IP) → 429 `auth_rate_limited` kèm Retry-After.
    Thông điệp như nhau dù email có tồn tại hay không.
    """
    ip = client_ip(request, get_settings().trusted_proxy_count)
    email_key = f"login-email:{normalize_email(data.email)}"  # đổi hoa/thường không né được
    ip_key = f"login-ip:{ip}"

    for kind, limiter, key in (("login_email", limits.login_email, email_key), ("login_ip", limits.login_ip, ip_key)):
        decision = limiter.check(key)
        if not decision.allowed:
            log_rejection(kind, ip=ip, retry_after=decision.retry_after)
            raise rate_limit_error(429, "auth_rate_limited", AUTH_LIMITED_MESSAGE, decision.retry_after)

    try:
        user = auth_service.authenticate(session, data)
    except AppError as error:
        if error.code == "invalid_credentials":
            limits.login_email.record(email_key)
            limits.login_ip.record(ip_key)
        raise
    limits.login_email.reset(email_key)  # đăng nhập đúng: xóa bộ đếm sai của email này
    token, expires_in = create_access_token(user.user_id)
    return TokenResponse(access_token=token, expires_in=expires_in)
