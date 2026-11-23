"""Dependency dùng chung cho route: session DB và người dùng hiện tại (từ Bearer token)."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.limits import AppLimits, get_limits
from app.core.security import InvalidTokenError, TokenExpiredError, decode_access_token
from app.db.session import get_db
from app.llm import get_llm_service
from app.llm.errors import LLMConfigError
from app.llm.service import LLMService
from app.models import User

DbSession = Annotated[Session, Depends(get_db)]

# auto_error=False: tự trả 401 theo định dạng lỗi chung thay vì 403 mặc định.
_bearer = HTTPBearer(auto_error=False, description="Access token từ /api/v1/auth/login")
_WWW_AUTHENTICATE = {"WWW-Authenticate": "Bearer"}


def _unauthorized(code: str, message: str) -> AppError:
    return AppError(401, code, message, headers=_WWW_AUTHENTICATE)


def get_current_user(
    session: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None:
        raise _unauthorized("not_authenticated", "Bạn cần đăng nhập.")
    try:
        user_id = decode_access_token(credentials.credentials)
    except TokenExpiredError:
        raise _unauthorized("token_expired", "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.") from None
    except InvalidTokenError:
        raise _unauthorized("invalid_token", "Phiên đăng nhập không hợp lệ.") from None

    user = session.get(User, user_id)
    if user is None:  # token hợp lệ nhưng tài khoản không còn
        raise _unauthorized("invalid_token", "Phiên đăng nhập không hợp lệ.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_llm() -> LLMService:
    """LLM dùng cho request. Test thay bằng FakeLLM qua dependency_overrides."""
    try:
        return get_llm_service()
    except LLMConfigError:
        raise AppError(503, "llm_not_configured", "Gia sư AI chưa được cấu hình trên máy chủ.") from None


LLM = Annotated[LLMService, Depends(get_llm)]
Limits = Annotated[AppLimits, Depends(get_limits)]
