"""Chọn lịch sử gửi cho LLM (hàm thuần, không DB, không nhà cung cấp).

Quy tắc (quyết định Tuần 3, mục 4–5):
- Chỉ gửi các lượt HOÀN CHỈNH: tin người dùng + trả lời `ok` của trợ lý.
- Tin người dùng mà trả lời bị lỗi (status `error`) bị bỏ, cùng dòng lỗi: không gửi lại lỗi cho LLM.
- Giữ tối đa `max_turns` lượt gần nhất (mỗi lượt = 2 tin), theo đúng thứ tự thời gian.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.llm.types import ChatMessage

USER = "user"
ASSISTANT = "assistant"
STATUS_OK = "ok"


@dataclass(frozen=True)
class StoredMessage:
    """Dạng tối thiểu của một tin đã lưu, đọc từ DB theo thứ tự thời gian."""

    role: str
    content: str
    status: str = STATUS_OK


def build_history(messages: Sequence[StoredMessage], max_turns: int) -> tuple[ChatMessage, ...]:
    if max_turns <= 0:
        return ()
    turns: list[tuple[ChatMessage, ChatMessage]] = []
    pending_user: StoredMessage | None = None
    for message in messages:
        if message.role == USER:
            pending_user = message  # tin người dùng chưa có trả lời → chỉ giữ tin mới nhất
        elif message.role == ASSISTANT:
            if pending_user is not None and message.status == STATUS_OK:
                turns.append((ChatMessage(USER, pending_user.content), ChatMessage(ASSISTANT, message.content)))
            pending_user = None  # trả lời lỗi hoặc mồ côi: bỏ cả lượt
    kept = turns[-max_turns:]
    return tuple(message for turn in kept for message in turn)
