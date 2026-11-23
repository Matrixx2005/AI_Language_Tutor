"""Cấu hình ứng dụng, đọc từ biến môi trường hoặc file `.env` ở thư mục gốc dự án."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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

    # LLM (dùng chung, không chứa thông tin riêng của nhà cung cấp; key nằm ở module nhà cung cấp).
    llm_provider: str = "fake"  # an toàn mặc định: không gọi mạng, không tốn hạn mức
    llm_model_id: str = ""
    llm_fallback_model_ids: str = ""  # cách nhau bằng dấu phẩy; dùng khi model chính hết hạn mức
    llm_timeout_seconds: float = Field(default=30.0, gt=0, le=120)
    llm_max_retries: int = Field(default=1, ge=0, le=3)  # ít, để tiết kiệm hạn mức gói miễn phí
    llm_max_output_tokens: int = Field(default=1024, ge=64, le=8192)

    # Chat (quyết định Tuần 3, mục 4): gửi N lượt gần nhất; giới hạn độ dài mỗi tin người dùng.
    chat_history_turns: int = Field(default=10, ge=0, le=50)
    chat_max_message_chars: int = Field(default=2000, ge=1, le=10_000)

    # Giới hạn tần suất (Tuần 3, Buổi 4). 0 = tắt giới hạn đó. Bộ đếm phút/IP nằm trong bộ nhớ
    # (chỉ đúng khi chạy MỘT tiến trình); giới hạn NGÀY đếm từ DB.
    chat_user_per_minute: int = Field(default=6, ge=0, le=1000)
    chat_user_per_day: int = Field(default=40, ge=0, le=100_000)
    chat_max_concurrent_per_user: int = Field(default=1, ge=1, le=10)
    # Ngưỡng TOÀN HỆ THỐNG (cả app dùng chung một key): gói free gemini-3.5-flash-lite 15 RPM →
    # mặc định 10 để chừa dư địa cho thử lại/model dự phòng. RPD chưa biết → mặc định tắt.
    llm_global_per_minute: int = Field(default=10, ge=0, le=100_000)
    llm_global_per_day: int = Field(default=0, ge=0, le=10_000_000)
    auth_login_fails_per_email: int = Field(default=5, ge=0, le=1000)
    auth_login_fails_per_ip: int = Field(default=20, ge=0, le=100_000)
    auth_login_window_seconds: int = Field(default=900, ge=60, le=86_400)
    auth_register_per_ip_per_hour: int = Field(default=10, ge=0, le=100_000)
    user_timezone: str = "Asia/Ho_Chi_Minh"  # ranh giới "ngày" cho giới hạn theo ngày
    # Số proxy tin cậy đứng trước app. 0 = KHÔNG tin X-Forwarded-For (dễ giả mạo), chỉ dùng IP kết nối.
    # Chỉ đặt > 0 khi triển khai sau reverse proxy mà mình kiểm soát (Tuần 8).
    trusted_proxy_count: int = Field(default=0, ge=0, le=5)

    @field_validator("user_timezone")
    @classmethod
    def _valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"USER_TIMEZONE không hợp lệ: {value!r}") from exc
        return value

    def llm_fallback_model_id_list(self) -> list[str]:
        return [model.strip() for model in self.llm_fallback_model_ids.split(",") if model.strip()]

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
