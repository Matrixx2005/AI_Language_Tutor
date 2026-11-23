"""Nghiệp vụ chat với gia sư AI (baseline LLM-only, chưa RAG).

Chính sách khi LLM lỗi (quyết định Tuần 3, mục 5): tin người dùng đã được lưu TRƯỚC khi gọi LLM;
nếu LLM lỗi thì lưu thêm một dòng trợ lý `status='error'` kèm mã lỗi chuẩn hóa. Dòng lỗi và tin
người dùng tương ứng không được gửi lại cho LLM (xem chat_history.build_history).
Log chỉ ghi metadata (độ dài, độ trễ, token, mã lỗi) — không ghi nội dung tin nhắn.
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.languages import get_language_config
from app.core.prompts import render_prompt
from app.llm.errors import LLMError
from app.llm.service import LLMService
from app.llm.types import ChatMessage, LLMRequest, LLMResult
from app.models import ChatMessageRow, ChatSession, User
from app.services.chat_history import StoredMessage, build_history

logger = logging.getLogger("app.chat")

HISTORY_SCAN_LIMIT = 200  # số tin gần nhất đọc từ DB để dựng lịch sử (đủ cho 50 lượt kể cả lỗi)
TITLE_LENGTH = 60

# Mã lỗi LLM chuẩn hóa → HTTP + thông điệp tiếng Việt. Không lộ chi tiết nhà cung cấp.
_LLM_ERROR_HTTP: dict[str, tuple[int, str]] = {
    "llm_rate_limited": (429, "Gia sư AI đang quá tải. Vui lòng thử lại sau ít phút."),
    "llm_quota_exhausted": (429, "Gia sư AI đã hết lượt dùng trong hôm nay. Vui lòng thử lại sau."),
    "llm_timeout": (504, "Gia sư AI phản hồi quá lâu. Vui lòng thử lại."),
    "llm_provider_error": (502, "Gia sư AI tạm thời không phản hồi. Vui lòng thử lại."),
    "llm_invalid_response": (502, "Gia sư AI trả lời không hợp lệ. Vui lòng thử lại."),
    "llm_content_blocked": (422, "Nội dung này không thể xử lý. Hãy diễn đạt câu hỏi theo cách khác."),
    "llm_not_configured": (503, "Gia sư AI chưa được cấu hình trên máy chủ."),
}


def llm_error_to_app_error(error: LLMError) -> AppError:
    status, message = _LLM_ERROR_HTTP.get(error.code, (502, "Gia sư AI gặp lỗi. Vui lòng thử lại."))
    headers = None
    if status == 429 and error.retry_after is not None:
        headers = {"Retry-After": str(max(1, round(error.retry_after)))}
    return AppError(status, error.code, message, headers=headers)


def _session_not_found() -> AppError:
    # 404 cho cả "không tồn tại" lẫn "của người khác": không xác nhận phiên của người khác tồn tại.
    return AppError(404, "chat_session_not_found", "Không tìm thấy cuộc trò chuyện.")


def get_own_session(db: Session, user: User, session_id: uuid.UUID) -> ChatSession:
    chat = db.scalar(
        select(ChatSession).where(ChatSession.session_id == session_id, ChatSession.user_id == user.user_id)
    )
    if chat is None:
        raise _session_not_found()
    return chat


def create_session(db: Session, user: User) -> ChatSession:
    profile = user.profile
    if profile is None:
        raise AppError(404, "profile_not_found", "Không tìm thấy hồ sơ học tập.")
    chat = ChatSession(
        user_id=user.user_id,
        language_code=profile.language_code,
        level_code=profile.current_level_code,
        retrieval_mode="llm_only",
    )
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat


def list_sessions(db: Session, user: User, limit: int = 50) -> list[ChatSession]:
    return list(
        db.scalars(
            select(ChatSession)
            .where(ChatSession.user_id == user.user_id)
            .order_by(ChatSession.updated_at.desc(), ChatSession.created_at.desc())
            .limit(limit)
        )
    )


def list_messages(db: Session, user: User, session_id: uuid.UUID, limit: int = 500) -> list[ChatMessageRow]:
    get_own_session(db, user, session_id)
    return list(
        db.scalars(
            select(ChatMessageRow)
            .where(ChatMessageRow.session_id == session_id)
            .order_by(ChatMessageRow.created_at, ChatMessageRow.message_id)
            .limit(limit)
        )
    )


def _recent_messages(db: Session, session_id: uuid.UUID) -> list[StoredMessage]:
    rows = db.execute(
        select(ChatMessageRow.role, ChatMessageRow.content, ChatMessageRow.status)
        .where(ChatMessageRow.session_id == session_id)
        .order_by(ChatMessageRow.created_at.desc(), ChatMessageRow.message_id.desc())
        .limit(HISTORY_SCAN_LIMIT)
    ).all()
    return [StoredMessage(role, content, status) for role, content, status in reversed(rows)]


def _system_prompt(language_code: str, level_code: str) -> str:
    language = get_language_config(language_code)
    level = next((lv for lv in language.levels if lv.code == level_code), None)
    level_name = level.display_name_vi if level else level_code
    return render_prompt(language_code, "tutor", level_code=level_code, level_name=level_name)


def send_message(
    db: Session, llm: LLMService, user: User, session_id: uuid.UUID, content: str
) -> tuple[ChatMessageRow, ChatMessageRow]:
    settings = get_settings()
    chat = get_own_session(db, user, session_id)
    if len(content) > settings.chat_max_message_chars:
        raise AppError(
            422, "message_too_long", f"Tin nhắn dài tối đa {settings.chat_max_message_chars} ký tự."
        )

    history = build_history(_recent_messages(db, chat.session_id), settings.chat_history_turns)
    level_code = user.profile.current_level_code if user.profile else (chat.level_code or "")
    system_prompt = _system_prompt(chat.language_code, level_code)

    # 1) Lưu tin người dùng và commit TRƯỚC khi gọi LLM (không giữ transaction trong lúc chờ).
    user_row = ChatMessageRow(
        session_id=chat.session_id, language_code=chat.language_code, role="user", content=content
    )
    db.add(user_row)
    if chat.title is None:
        chat.title = " ".join(content.split())[:TITLE_LENGTH]
    db.commit()
    db.refresh(user_row)

    # 2) Gọi LLM: nội dung người dùng chỉ nằm trong danh sách tin nhắn, không ghép vào system prompt.
    request = LLMRequest(system_prompt=system_prompt, messages=(*history, ChatMessage("user", content)))
    try:
        result: LLMResult = llm.generate(request)
    except LLMError as error:
        error_row = ChatMessageRow(
            session_id=chat.session_id,
            language_code=chat.language_code,
            role="assistant",
            content="",
            status="error",
            error_code=error.code,
        )
        db.add(error_row)
        chat.updated_at = _now_marker()
        db.commit()
        logger.warning(
            "chat llm_error session=%s code=%s history_messages=%d message_chars=%d",
            chat.session_id, error.code, len(history), len(content),
        )
        raise llm_error_to_app_error(error) from None

    # 3) Lưu trả lời kèm metadata (model, token, độ trễ, bị cắt).
    assistant_row = ChatMessageRow(
        session_id=chat.session_id,
        language_code=chat.language_code,
        role="assistant",
        content=result.text,
        model_id=result.model,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        latency_ms=result.latency_ms,
        truncated=result.truncated,
    )
    db.add(assistant_row)
    chat.updated_at = _now_marker()
    db.commit()
    db.refresh(assistant_row)
    logger.info(
        "chat ok session=%s history_messages=%d message_chars=%d reply_chars=%d latency_ms=%d "
        "in_tokens=%s out_tokens=%s truncated=%s",
        chat.session_id, len(history), len(content), len(result.text), result.latency_ms,
        result.input_tokens, result.output_tokens, result.truncated,
    )
    return user_row, assistant_row


def _now_marker():
    # clock_timestamp(): thời điểm thật lúc ghi (now() sẽ trả thời điểm bắt đầu transaction).
    return func.clock_timestamp()
