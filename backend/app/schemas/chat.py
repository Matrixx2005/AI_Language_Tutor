from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

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
    model_config = ConfigDict(extra="forbid")

    content: MessageText


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


class ChatTurnRead(BaseModel):
    user_message: ChatMessageRead
    assistant_message: ChatMessageRead
    has_citations: bool = Field(default=False, description="Tuần 3 chưa có RAG: luôn false")
