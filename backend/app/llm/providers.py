"""Danh bạ nhà cung cấp: nơi DUY NHẤT ánh xạ tên trong LLM_PROVIDER sang lớp cài đặt.

Mỗi nhà cung cấp là một hàm tạo nhận Settings, import lười để không cần cài SDK của nhà
cung cấp không dùng (ví dụ chạy test với `fake` không cần SDK Gemini).
"""
from __future__ import annotations

from collections.abc import Callable

from app.core.config import Settings
from app.llm.errors import LLMConfigError
from app.llm.provider import LLMProvider


def _fake(_: Settings) -> LLMProvider:
    from app.llm.fake import FakeLLM

    return FakeLLM()


def _gemini(_: Settings) -> LLMProvider:
    from app.llm.gemini import create_gemini_provider  # key chỉ được đọc trong module này

    return create_gemini_provider()


PROVIDERS: dict[str, Callable[[Settings], LLMProvider]] = {
    "fake": _fake,
    "gemini": _gemini,
}


def create_provider(settings: Settings) -> LLMProvider:
    factory = PROVIDERS.get(settings.llm_provider.strip().lower())
    if factory is None:
        raise LLMConfigError(f"LLM_PROVIDER không hỗ trợ: {settings.llm_provider!r}")
    return factory(settings)
