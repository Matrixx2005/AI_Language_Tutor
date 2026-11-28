from __future__ import annotations

import unicodedata
import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

MAX_MESSAGE_LINES = 100

# Trần cứng chống gói tin khổng lồ; giới hạn thật (CHAT_MAX_MESSAGE_CHARS) kiểm ở service.
MessageText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20_000)]


class ChatSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: uuid.UUID
    language_code: str
    level_code: str | None
    retrieval_mode: str
    title: str | None
    created_at: datetime
    updated_at: datetime


class ChatMessageCreate(BaseModel):
    """An toàn đầu vào ở mức tối thiểu: bỏ ký tự điều khiển/NUL (giữ xuống dòng và tab), chuẩn hóa
    xuống dòng, giới hạn số dòng. KHÔNG lọc từ khóa kiểu "ignore instructions": chống prompt
    injection dựa vào cấu trúc (nội dung người dùng chỉ nằm trong danh sách tin nhắn)."""

    model_config = ConfigDict(extra="forbid")

    content: MessageText
    # Chế độ trả lời cho riêng tin này; bỏ trống = RAG_MODE của máy chủ. Giá trị lạ → 422.
    rag_mode: Literal["llm_only", "dense", "hybrid"] | None = None

    @field_validator("content", mode="before")
    @classmethod
    def _strip_control_characters(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        value = value.replace("\r\n", "\n").replace("\r", "\n")
        return "".join(ch for ch in value if ch in "\n\t" or unicodedata.category(ch) != "Cc")

    @field_validator("content")
    @classmethod
    def _limit_lines(cls, value: str) -> str:
        if value.count("\n") + 1 > MAX_MESSAGE_LINES:
            raise ValueError(f"Tin nhắn có tối đa {MAX_MESSAGE_LINES} dòng")
        return value


class SourceRead(BaseModel):
    """Tài liệu đã truy xuất cho một câu trả lời RAG; `n` là số dùng trong trích dẫn [n]."""

    n: int
    document_id: str
    title: str
    level: str
    rank: int
    score: float
    text: str
    cited: bool


class ChatMessageRead(BaseModel):
    """Không trả model/token/độ trễ cho frontend (chi tiết nội bộ, chỉ lưu DB)."""

    model_config = ConfigDict(from_attributes=True)

    message_id: uuid.UUID
    role: str
    content: str
    status: str
    error_code: str | None
    truncated: bool
    created_at: datetime
    rag_mode: str | None = None  # chế độ THỰC SỰ dùng (llm_only khi hạ cấp); None ở dòng người dùng
    rag_fallback: bool = False
    sources: list[SourceRead] | None = None
    citations: dict[str, Any] | None = Field(default=None, exclude=True)

    @property
    def invalid_citations(self) -> list[int]:
        return list((self.citations or {}).get("invalid", []))


class ChatTurnRead(BaseModel):
    user_message: ChatMessageRead
    assistant_message: ChatMessageRead
    has_citations: bool = Field(default=False, description="Câu trả lời có ít nhất một trích dẫn [n] hợp lệ")


class RagConfigRead(BaseModel):
    default_mode: str
    modes: list[str]
    top_k: int
