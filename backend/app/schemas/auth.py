from __future__ import annotations

from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    StringConstraints,
    field_validator,
    model_validator,
)

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128  # chặn chuỗi cực dài làm tốn CPU khi băm

DisplayName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


def normalize_email(value: str) -> str:
    """Khớp ràng buộc DB ck_users_email_normalized: email = lower(btrim(email))."""
    return value.strip().lower()


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(max_length=320)
    # SecretStr: không lộ mật khẩu khi log/repr đối tượng.
    password: SecretStr
    display_name: DisplayName | None = None

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        return normalize_email(value)

    @field_validator("password")
    @classmethod
    def _password_length(cls, value: SecretStr) -> SecretStr:
        length = len(value.get_secret_value())
        if not PASSWORD_MIN_LENGTH <= length <= PASSWORD_MAX_LENGTH:
            raise ValueError(
                f"Mật khẩu phải dài từ {PASSWORD_MIN_LENGTH} đến {PASSWORD_MAX_LENGTH} ký tự"
            )
        return value

    @model_validator(mode="after")
    def _password_differs_from_email(self) -> RegisterRequest:
        if self.password.get_secret_value().strip().lower() == self.email:
            raise ValueError("Mật khẩu không được trùng với email")
        return self


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(max_length=320)
    password: SecretStr

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        return normalize_email(value)

    @field_validator("password")
    @classmethod
    def _password_not_too_long(cls, value: SecretStr) -> SecretStr:
        # Không áp độ dài tối thiểu khi đăng nhập (tài khoản cũ có thể theo chính sách cũ).
        if len(value.get_secret_value()) > PASSWORD_MAX_LENGTH:
            raise ValueError(f"Mật khẩu dài tối đa {PASSWORD_MAX_LENGTH} ký tự")
        return value


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(description="Số giây đến khi token hết hạn")
