import uuid
from typing import Annotated

from fastapi import APIRouter, Body, status

from app.api.deps import LLM, CurrentUser, DbSession
from app.schemas.chat import ChatMessageCreate, ChatMessageRead, ChatSessionRead, ChatTurnRead
from app.services import chat as chat_service

# Mọi route đều lọc theo người dùng hiện tại; phiên của người khác → 404 (không phải 403).
router = APIRouter(prefix="/chat", tags=["chat"])

MESSAGE_EXAMPLES = {
    "a_an": {"summary": "Hỏi về a/an", "value": {"content": "Khi nào dùng 'a' và khi nào dùng 'an'?"}},
    "thi": {"summary": "Hỏi về thì", "value": {"content": "Present perfect khác past simple thế nào?"}},
}


@router.post("/sessions", status_code=status.HTTP_201_CREATED, response_model=ChatSessionRead)
def create_session(user: CurrentUser, db: DbSession) -> ChatSessionRead:
    """Tạo cuộc trò chuyện mới theo ngôn ngữ và trình độ hiện tại trong hồ sơ."""
    return ChatSessionRead.model_validate(chat_service.create_session(db, user))


@router.get("/sessions", response_model=list[ChatSessionRead])
def list_sessions(user: CurrentUser, db: DbSession) -> list[ChatSessionRead]:
    """50 cuộc trò chuyện gần nhất của chính mình."""
    return [ChatSessionRead.model_validate(chat) for chat in chat_service.list_sessions(db, user)]


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageRead])
def list_messages(session_id: uuid.UUID, user: CurrentUser, db: DbSession) -> list[ChatMessageRead]:
    """Lịch sử theo thứ tự thời gian, gồm cả lượt lỗi (status='error')."""
    return [ChatMessageRead.model_validate(row) for row in chat_service.list_messages(db, user, session_id)]


@router.post("/sessions/{session_id}/messages", response_model=ChatTurnRead)
def send_message(
    session_id: uuid.UUID,
    data: Annotated[ChatMessageCreate, Body(openapi_examples=MESSAGE_EXAMPLES)],
    user: CurrentUser,
    db: DbSession,
    llm: LLM,
) -> ChatTurnRead:
    """Gửi tin và nhận trả lời (không streaming). Khi AI lỗi: tin của bạn vẫn được lưu, API trả mã lỗi
    ổn định (`llm_timeout`, `llm_rate_limited`, ...) và lịch sử có một dòng trả lời `status='error'`."""
    user_row, assistant_row = chat_service.send_message(db, llm, user, session_id, data.content)
    return ChatTurnRead(
        user_message=ChatMessageRead.model_validate(user_row),
        assistant_message=ChatMessageRead.model_validate(assistant_row),
    )
