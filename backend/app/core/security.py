"""Băm mật khẩu (Argon2id) và JWT access token."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings

JWT_ALGORITHM = "HS256"  # cố định; decode chỉ chấp nhận thuật toán này (chặn alg=none/đổi thuật toán)
JWT_ISSUER = "ai-language-tutor"
TOKEN_TYPE_ACCESS = "access"

_password_hash = PasswordHash.recommended()  # Argon2id, m=64MiB t=3 p=4
# Hash giả để khi email không tồn tại vẫn tốn thời gian như khi sai mật khẩu.
_DUMMY_HASH = _password_hash.hash("dummy-password-for-timing")


class InvalidTokenError(Exception):
    """Token sai chữ ký, sai định dạng hoặc thiếu trường bắt buộc."""


class TokenExpiredError(InvalidTokenError):
    """Token đúng chữ ký nhưng đã hết hạn."""


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> tuple[bool, str | None]:
    """Trả (đúng/sai, hash mới nếu tham số cũ cần nâng cấp)."""
    return _password_hash.verify_and_update(password, password_hash)


def burn_password_check(password: str) -> None:
    _password_hash.verify(password, _DUMMY_HASH)


def create_access_token(user_id: uuid.UUID, *, now: datetime | None = None) -> tuple[str, int]:
    settings = get_settings()
    issued_at = now or datetime.now(UTC)
    lifetime = timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "type": TOKEN_TYPE_ACCESS,
        "iss": JWT_ISSUER,
        "iat": issued_at,
        "exp": issued_at + lifetime,
    }
    token = jwt.encode(payload, settings.require_jwt_secret(), algorithm=JWT_ALGORITHM)
    return token, int(lifetime.total_seconds())


def decode_access_token(token: str) -> uuid.UUID:
    try:
        payload = jwt.decode(
            token,
            get_settings().require_jwt_secret(),
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
            options={"require": ["exp", "iat", "iss", "sub"]},
        )
        if payload.get("type") != TOKEN_TYPE_ACCESS:
            raise InvalidTokenError("sai loại token")
        return uuid.UUID(payload["sub"])
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredError("token hết hạn") from exc
    except (jwt.InvalidTokenError, ValueError, TypeError) as exc:
        raise InvalidTokenError("token không hợp lệ") from exc
