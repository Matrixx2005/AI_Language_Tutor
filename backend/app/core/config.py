"""Cấu hình ứng dụng, đọc từ biến môi trường hoặc file `.env` ở thư mục gốc dự án."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MIN_JWT_SECRET_LENGTH = 32
DEV_CORS_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")  # Vite dev server


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",  # .env còn chứa biến của tuần sau (LLM, Qdrant...)
    )

    app_name: str = "AI Language Tutor"
    environment: str = "development"

    # PostgreSQL: cùng các biến này được docker-compose.yml dùng để tạo DB.
    # Dùng 127.0.0.1, không dùng "localhost": Windows thử IPv6 ::1 trước, mà Docker chỉ
    # bind 127.0.0.1 → mỗi kết nối chậm/treo (đo được 8s so với 0,04s).
    postgres_host: str = "127.0.0.1"
    postgres_connect_timeout: int = 10  # giây; DB chưa chạy thì báo lỗi thay vì treo
    postgres_port: int = 5432
    postgres_user: str = "tutor"
    postgres_password: SecretStr | None = None
    postgres_db: str = "ai_language_tutor"
    postgres_test_db: str = "ai_language_tutor_test"

    default_language_code: str = "en"

    # CORS: danh sách origin cách nhau bằng dấu phẩy. Để trống → development dùng
    # DEV_CORS_ORIGINS (Vite), môi trường khác tắt CORS.
    cors_origins: str = ""

    @field_validator("cors_origins")
    @classmethod
    def _no_wildcard_origin(cls, value: str) -> str:
        if "*" in value:
            raise ValueError("CORS_ORIGINS không được chứa '*'; liệt kê từng origin cụ thể")
        return value

    def effective_cors_origins(self) -> list[str]:
        configured = [origin.strip().rstrip("/") for origin in self.cors_origins.split(",") if origin.strip()]
        if configured:
            return configured
        return list(DEV_CORS_ORIGINS) if self.environment == "development" else []

    # JWT: secret chỉ đọc từ .env; thuật toán cố định trong app.core.security.
    jwt_secret: SecretStr | None = None
    access_token_expire_minutes: int = Field(default=60, ge=1, le=24 * 60)

    @field_validator("jwt_secret")
    @classmethod
    def _secret_long_enough(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None and len(value.get_secret_value()) < MIN_JWT_SECRET_LENGTH:
            raise ValueError(f"JWT_SECRET phải dài ít nhất {MIN_JWT_SECRET_LENGTH} ký tự")
        return value

    def require_jwt_secret(self) -> str:
        if self.jwt_secret is None:
            raise RuntimeError("JWT_SECRET chưa được đặt trong .env")
        return self.jwt_secret.get_secret_value()

    def database_url(self, *, test: bool = False) -> URL:
        """URL SQLAlchemy; mật khẩu được escape đúng, không ghép chuỗi thủ công."""
        if self.postgres_password is None:
            raise RuntimeError("POSTGRES_PASSWORD chưa được đặt trong .env")
        return URL.create(
            "postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_test_db if test else self.postgres_db,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
