"""Cấu hình ứng dụng, đọc từ biến môi trường hoặc file `.env` ở thư mục gốc dự án."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

PROJECT_ROOT = Path(__file__).resolve().parents[3]


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
