"""Kiểu dữ liệu dùng chung giữa LLMService và các nhà cung cấp."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel

Role = Literal["user", "assistant"]


@dataclass(frozen=True)
class ChatMessage:
    role: Role
    content: str

    def __repr__(self) -> str:  # không in nội dung tin nhắn vào log/traceback
        return f"ChatMessage(role={self.role!r}, length={len(self.content)})"


@dataclass(frozen=True)
class LLMRequest:
    system_prompt: str
    messages: tuple[ChatMessage, ...]
    response_schema: type[BaseModel] | None = None  # structured output (tùy chọn)
    max_output_tokens: int | None = None

    def __repr__(self) -> str:
        return (
            f"LLMRequest(messages={len(self.messages)}, "
            f"schema={getattr(self.response_schema, '__name__', None)})"
        )


@dataclass(frozen=True)
class ProviderResponse:
    """Kết quả thô một lần gọi nhà cung cấp."""

    text: str
    model: str  # model thực tế phản hồi (có thể khác model yêu cầu)
    input_tokens: int | None = None
    output_tokens: int | None = None
    truncated: bool = False  # bị cắt vì chạm giới hạn token đầu ra nhưng vẫn có văn bản

    def __repr__(self) -> str:  # không in nội dung trả lời
        return (
            f"ProviderResponse(model={self.model!r}, length={len(self.text)}, "
            f"input_tokens={self.input_tokens}, output_tokens={self.output_tokens}, truncated={self.truncated})"
        )


@dataclass(frozen=True)
class LLMResult:
    text: str
    model: str
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int  # tổng thời gian, gồm cả thử lại
    attempts: int  # tổng số lần gọi nhà cung cấp
    parsed: BaseModel | None = None
    fallback_used: bool = False
    requested_model: str = field(default="")
    truncated: bool = False

    def __repr__(self) -> str:
        return (
            f"LLMResult(model={self.model!r}, attempts={self.attempts}, latency_ms={self.latency_ms}, "
            f"input_tokens={self.input_tokens}, output_tokens={self.output_tokens}, "
            f"truncated={self.truncated}, length={len(self.text)})"
        )
