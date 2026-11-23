"""Lớp LLM dùng chung. Code nghiệp vụ chỉ dùng `get_llm_service()` và các kiểu trong app.llm.types."""
from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.llm.errors import LLMConfigError
from app.llm.providers import create_provider
from app.llm.service import LLMService


def build_llm_service(settings=None) -> LLMService:
    settings = settings or get_settings()
    provider = create_provider(settings)
    model = settings.llm_model_id.strip() or provider.default_model
    if not model:
        raise LLMConfigError("LLM_MODEL_ID chưa được đặt trong .env")
    return LLMService(
        provider,
        model=model,
        fallback_models=settings.llm_fallback_model_id_list(),
        timeout_seconds=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
        default_max_output_tokens=settings.llm_max_output_tokens,
    )


@lru_cache
def get_llm_service() -> LLMService:
    """Dependency FastAPI (Buổi 3). Tạo lười: app khởi động được khi LLM chưa cấu hình."""
    return build_llm_service()
