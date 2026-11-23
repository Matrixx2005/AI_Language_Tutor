"""Giao diện nhà cung cấp LLM. Mỗi nhà cung cấp chỉ cài đặt một lần gọi; thử lại, timeout
tổng, model dự phòng và kiểm tra structured output do LLMService đảm nhiệm.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.llm.types import LLMRequest, ProviderResponse


class LLMProvider(ABC):
    name: str = "abstract"
    default_model: str | None = None  # dùng khi LLM_MODEL_ID trống (chỉ nhà cung cấp giả nên đặt)

    @abstractmethod
    def generate(self, request: LLMRequest, *, model: str, timeout_seconds: float) -> ProviderResponse:
        """Gọi đúng MỘT lần (không tự thử lại). Lỗi phải là app.llm.errors.LLMError."""

    def __repr__(self) -> str:  # lớp con không được in key/secret
        return f"{type(self).__name__}(name={self.name!r})"
