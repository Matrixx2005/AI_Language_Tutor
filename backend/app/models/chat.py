"""chat_sessions, chat_messages theo ERD đã duyệt + bổ sung đã duyệt ở Tuần 3 (quyết định 7):
title; status, error_code, model_id, input_tokens, output_tokens, latency_ms (và truncated).
Khóa ngoại RESTRICT: chính sách xóa dữ liệu chưa chốt (docs/DATABASE_DESIGN.md).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User

CODE_LENGTH = 16


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    __table_args__ = (Index("ix_chat_sessions_user_id_updated_at", "user_id", text("updated_at DESC")),)

    session_id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id", ondelete="RESTRICT"))
    language_code: Mapped[str] = mapped_column(String(CODE_LENGTH), server_default="en")
    level_code: Mapped[str | None] = mapped_column(String(CODE_LENGTH))  # trình độ lúc tạo phiên
    retrieval_mode: Mapped[str] = mapped_column(String(32), server_default="llm_only")
    title: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship()
    messages: Mapped[list[ChatMessageRow]] = relationship(
        back_populates="session", order_by="ChatMessageRow.created_at", lazy="raise"
    )

    def __repr__(self) -> str:  # không in title (có thể chứa nội dung người dùng)
        return f"ChatSession(session_id={self.session_id})"


class ChatMessageRow(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="role_valid"),
        CheckConstraint("status IN ('ok', 'error')", name="status_valid"),
        CheckConstraint("status = 'ok' OR error_code IS NOT NULL", name="error_has_code"),
        Index("ix_chat_messages_session_id_created_at", "session_id", "created_at"),
    )

    message_id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chat_sessions.session_id", ondelete="RESTRICT"))
    language_code: Mapped[str] = mapped_column(String(CODE_LENGTH), server_default="en")
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text, server_default="")
    # RAG (Tuần 4) — chỉ có ý nghĩa ở dòng trợ lý:
    # citations: {"valid": [n...], "invalid": [n...]} — số trích dẫn hợp lệ / bị loại vì ngoài tập truy xuất.
    citations: Mapped[Any | None] = mapped_column(JSONB)
    # Chế độ THỰC SỰ dùng cho lượt này (llm_only khi hạ cấp); NULL với dòng người dùng và dữ liệu Tuần 3.
    rag_mode: Mapped[str | None] = mapped_column(String(16))
    # Tài liệu đã truy xuất: [{n, document_id, title, level, rank, score, text, cited}]. NULL khi llm_only.
    sources: Mapped[Any | None] = mapped_column(JSONB)
    # True khi người dùng chọn RAG nhưng hạ tầng truy xuất lỗi → trả lời bằng llm_only.
    rag_fallback: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    status: Mapped[str] = mapped_column(String(16), server_default="ok")
    error_code: Mapped[str | None] = mapped_column(String(64))
    model_id: Mapped[str | None] = mapped_column(String(100))
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    truncated: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    # clock_timestamp(): hai tin trong cùng transaction vẫn có thời điểm khác nhau → thứ tự ổn định.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())

    session: Mapped[ChatSession] = relationship(back_populates="messages")

    def __repr__(self) -> str:  # không in nội dung tin nhắn
        return f"ChatMessageRow(message_id={self.message_id}, role={self.role!r}, status={self.status!r})"
