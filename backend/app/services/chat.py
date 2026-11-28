"""Nghiệp vụ chat với gia sư AI (baseline LLM-only, chưa RAG).

Chính sách khi LLM lỗi (quyết định Tuần 3, mục 5): tin người dùng đã được lưu TRƯỚC khi gọi LLM;
nếu LLM lỗi thì lưu thêm một dòng trợ lý `status='error'` kèm mã lỗi chuẩn hóa. Dòng lỗi và tin
người dùng tương ứng không được gửi lại cho LLM (xem chat_history.build_history).
Log chỉ ghi metadata (độ dài, độ trễ, token, mã lỗi) — không ghi nội dung tin nhắn.
"""
from __future__ import annotations

import logging
import re
import uuid

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core import limits as limits_module
from app.core.languages import get_language_config
from app.core.limits import (
    AppLimits,
    llm_cooldown_seconds,
    local_day_bounds,
    log_rejection,
    rate_limit_error,
    seconds_until_local_midnight,
)
from app.core.prompts import render_prompt
from app.llm.errors import LLMError
from app.llm.service import LLMService
from app.llm.types import ChatMessage, LLMRequest, LLMResult
from app.models import ChatMessageRow, ChatSession, User
from app.retrieval.citations import check_citations, format_context
from app.retrieval.confidence import dense_top_score
from app.retrieval.hybrid import HybridRetriever
from app.retrieval.rewrite import LLMRewriter, branch_queries
from app.retrieval.types import RetrievalError, RetrievedDoc
from app.services.chat_history import StoredMessage, build_history

logger = logging.getLogger("app.chat")

INTERNAL_ERROR = "internal_error"
SERVICE_BUSY_MESSAGE = "Hệ thống đang bận. Vui lòng thử lại sau ít phút."
# Tiền tố model_id cho câu trả lời của nhà cung cấp không tốn hạn mức (LLM_PROVIDER=fake).
FAKE_MODEL_PREFIX = "fake:"
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
    """`limit` tin MỚI NHẤT, trả theo thứ tự thời gian tăng dần (phiên dài không mất tin mới)."""
    get_own_session(db, user, session_id)
    newest_first = db.scalars(
        select(ChatMessageRow)
        .where(ChatMessageRow.session_id == session_id)
        .order_by(ChatMessageRow.created_at.desc(), ChatMessageRow.message_id.desc())
        .limit(limit)
    ).all()
    return list(reversed(newest_first))


def _recent_messages(db: Session, session_id: uuid.UUID) -> list[StoredMessage]:
    rows = db.execute(
        select(ChatMessageRow.role, ChatMessageRow.content, ChatMessageRow.status)
        .where(ChatMessageRow.session_id == session_id)
        .order_by(ChatMessageRow.created_at.desc(), ChatMessageRow.message_id.desc())
        .limit(HISTORY_SCAN_LIMIT)
    ).all()
    return [StoredMessage(role, content, status) for role, content, status in reversed(rows)]


def _system_prompt(language_code: str, level_code: str, docs: list[RetrievedDoc] | None = None) -> str:
    language = get_language_config(language_code)
    level = next((lv for lv in language.levels if lv.code == level_code), None)
    level_name = level.display_name_vi if level else level_code
    if docs is None:
        return render_prompt(language_code, "tutor", level_code=level_code, level_name=level_name)
    # Ngữ cảnh truy xuất là DỮ LIỆU trong khối phân cách; nội dung người dùng vẫn chỉ ở danh sách tin.
    return render_prompt(language_code, "tutor_rag", level_code=level_code, level_name=level_name,
                         context=format_context(docs))


def _low_confidence_prompt(language_code: str, level_code: str) -> str:
    language = get_language_config(language_code)
    level = next((lv for lv in language.levels if lv.code == level_code), None)
    return render_prompt(language_code, "tutor_low_confidence", level_code=level_code,
                         level_name=level.display_name_vi if level else level_code)


_CITATION_MARK = re.compile(r"\s?\[\d{1,2}(?:\s*,\s*\d{1,2})*\](?!\()")


def _strip_history_citations(history: tuple[ChatMessage, ...]) -> tuple[ChatMessage, ...]:
    """[n] ở các lượt trước trỏ tới ngữ cảnh CŨ: bỏ khi gửi lại cho LLM để không bị dùng nhầm số."""
    return tuple(
        ChatMessage(m.role, _CITATION_MARK.sub("", m.content)) if m.role == "assistant" else m for m in history
    )


def send_message(
    db: Session,
    llm: LLMService,
    user: User,
    session_id: uuid.UUID,
    content: str,
    limits: AppLimits | None = None,
    *,
    rag_mode: str | None = None,
    retriever_for=None,
) -> tuple[ChatMessageRow, ChatMessageRow]:
    """Thứ tự kiểm tra (Buổi 4): chủ sở hữu (404) → độ dài (422) → đồng thời (409) → giới hạn
    phút/ngày theo người dùng → ngưỡng toàn hệ thống → lưu tin → gọi LLM.
    Bị từ chối vì giới hạn: KHÔNG lưu tin, KHÔNG gọi LLM. `limits=None` chỉ dùng trong test nội bộ."""
    settings = get_settings()
    chat = get_own_session(db, user, session_id)
    if len(content) > settings.chat_max_message_chars:
        raise AppError(
            422, "message_too_long", f"Tin nhắn dài tối đa {settings.chat_max_message_chars} ký tự."
        )
    rag = _RagRequest(rag_mode or settings.rag_mode, retriever_for, llm)
    if limits is None:
        return _process_turn(db, llm, user, chat, content, settings, None, rag)

    user_key = str(user.user_id)
    if not limits.chat_in_flight.acquire(user_key, settings.chat_max_concurrent_per_user):
        log_rejection("chat_busy", user_id=user.user_id)
        raise AppError(409, "chat_busy", "Gia sư AI đang trả lời tin trước của bạn. Vui lòng đợi.")
    try:  # khóa "đang xử lý" LUÔN được nhả, kể cả khi bị từ chối, LLM lỗi hay exception lạ
        _enforce_limits(db, user, limits, settings, consumes_quota=_consumes_quota(llm))
        return _process_turn(db, llm, user, chat, content, settings, limits, rag)
    finally:
        limits.chat_in_flight.release(user_key)


def _consumes_quota(llm) -> bool:
    return getattr(llm, "consumes_quota", True)


def _enforce_limits(db: Session, user: User, limits: AppLimits, settings, *, consumes_quota: bool = True) -> None:
    """Giới hạn phút mỗi người và khóa đồng thời áp dụng cả khi LLM_PROVIDER=fake (chống spam).
    Giới hạn ngày không tính lượt `fake:`; ngưỡng toàn hệ thống/tạm khóa chỉ áp dụng khi gọi LLM thật."""
    user_key = str(user.user_id)
    minute = limits.chat_user_minute.check(user_key)
    if not minute.allowed:
        log_rejection("chat_user_minute", user_id=user.user_id, retry_after=minute.retry_after)
        raise rate_limit_error(429, "chat_rate_limited", "Bạn đang gửi tin hơi nhanh. Vui lòng đợi một chút.", minute.retry_after)

    now = limits_module.utcnow()
    start, end = local_day_bounds(now, settings.user_timezone)
    until_midnight = seconds_until_local_midnight(now, settings.user_timezone)
    if settings.chat_user_per_day and _user_messages_today(db, user.user_id, start, end) >= settings.chat_user_per_day:
        log_rejection("chat_user_day", user_id=user.user_id, retry_after=until_midnight)
        raise rate_limit_error(
            429, "chat_daily_limit_reached",
            "Bạn đã dùng hết lượt hỏi gia sư AI hôm nay. Hãy quay lại vào ngày mai.", until_midnight,
        )

    if not consumes_quota:  # câu trả lời giả lập: không tốn hạn mức nhà cung cấp
        limits.chat_user_minute.record(user_key)
        return

    cooldown = limits.llm_cooldown.remaining()
    if cooldown > 0:
        log_rejection("llm_cooldown", user_id=user.user_id, retry_after=cooldown)
        raise rate_limit_error(429, "service_busy", SERVICE_BUSY_MESSAGE, cooldown)
    if settings.llm_global_per_day and _all_messages_today(db, start, end) >= settings.llm_global_per_day:
        log_rejection("llm_global_day", user_id=user.user_id, retry_after=until_midnight)
        raise rate_limit_error(429, "service_busy", SERVICE_BUSY_MESSAGE, until_midnight)
    global_minute = limits.llm_global_minute.hit("llm")
    if not global_minute.allowed:
        log_rejection("llm_global_minute", user_id=user.user_id, retry_after=global_minute.retry_after)
        raise rate_limit_error(429, "service_busy", SERVICE_BUSY_MESSAGE, global_minute.retry_after)

    limits.chat_user_minute.record(user_key)  # chỉ tính lượt khi mọi kiểm tra đã qua


def _is_fake_turn():
    return ChatMessageRow.model_id.like(f"{FAKE_MODEL_PREFIX}%")


def _user_messages_today(db: Session, user_id: uuid.UUID, start, end) -> int:
    """Tin người dùng hôm nay (theo USER_TIMEZONE), TRỪ lượt hỏng do phía hệ thống/nhà cung cấp
    (quyết định Tuần 3, mục 5) và TRỪ lượt giả lập `fake:`; lượt bị chặn vì nội dung vẫn tính.
    Mỗi tin người dùng có đúng một dòng trợ lý (ok hoặc lỗi) → trừ theo dòng trợ lý."""
    in_window = (ChatMessageRow.created_at >= start, ChatMessageRow.created_at < end, ChatSession.user_id == user_id)
    sent = db.scalar(
        select(func.count()).select_from(ChatMessageRow).join(ChatSession)
        .where(ChatMessageRow.role == "user", *in_window)
    )
    not_counted = db.scalar(
        select(func.count()).select_from(ChatMessageRow).join(ChatSession)
        .where(
            ChatMessageRow.role == "assistant",
            or_(
                and_(ChatMessageRow.status == "error", ChatMessageRow.error_code != "llm_content_blocked"),
                _is_fake_turn(),
            ),
            *in_window,
        )
    )
    return max(0, (sent or 0) - (not_counted or 0))


def _all_messages_today(db: Session, start, end) -> int:
    """Số lượt gọi LLM THẬT hôm nay của cả hệ thống (lượt lỗi vẫn tốn hạn mức; lượt `fake:` thì không)."""
    in_window = (ChatMessageRow.created_at >= start, ChatMessageRow.created_at < end)
    sent = db.scalar(select(func.count()).select_from(ChatMessageRow).where(ChatMessageRow.role == "user", *in_window))
    fake = db.scalar(
        select(func.count()).select_from(ChatMessageRow)
        .where(ChatMessageRow.role == "assistant", _is_fake_turn(), *in_window)
    )
    return max(0, (sent or 0) - (fake or 0))


class _RagRequest:
    """Chế độ trả lời của một lượt + cách lấy retriever (route truyền vào; test thay bằng bản in-memory)."""

    def __init__(self, mode: str, retriever_for, llm=None):
        self.mode = mode
        self.retriever_for = retriever_for
        self.llm = llm  # dùng cho viết lại truy vấn khi RAG_QUERY_REWRITE bật
        self.rewrite_status = "off"


def _retrieve(rag: _RagRequest, query: str, language_code: str, level_code: str, settings) -> list[RetrievedDoc]:
    if rag.retriever_for is None:
        raise RetrievalError("Chưa cấu hình truy xuất")
    try:
        retriever = rag.retriever_for(rag.mode)
    except RetrievalError:
        raise
    except Exception as exc:  # không dựng được retriever (thiếu gói, cấu hình sai...)
        raise RetrievalError(f"Không dựng được retriever ({type(exc).__name__})") from exc
    level = level_code if settings.rag_filter_level else None
    if settings.rag_query_rewrite and rag.llm is not None:
        # B1: viết lại truy vấn (tắt mặc định). Lỗi LLM/định dạng → Rewrite(ok=False) → dùng câu gốc, không làm hỏng truy xuất.
        rewrite = LLMRewriter(rag.llm, language_code).rewrite_batch([("q", query)])["q"]
        rag.rewrite_status = "ok" if rewrite.ok else f"skipped:{rewrite.error}"
        sparse_q, dense_q = branch_queries(query, rewrite, "both")
        if isinstance(retriever, HybridRetriever):
            return retriever.search(query, language_code, settings.rag_top_k, level, sparse_query=sparse_q, dense_query=dense_q)
        return retriever.search(dense_q, language_code, settings.rag_top_k, level)
    return retriever.search(query, language_code, settings.rag_top_k, level)


def _process_turn(db: Session, llm: LLMService, user: User, chat: ChatSession, content: str, settings, limits,
                  rag: _RagRequest | None = None):
    rag = rag or _RagRequest("llm_only", None)
    # 0) Đọc trước mọi giá trị cần dùng vào biến cục bộ: sau commit không được chạm DB khi chờ LLM.
    fake_prefix = "" if _consumes_quota(llm) else FAKE_MODEL_PREFIX
    chat_id = chat.session_id
    language_code = chat.language_code
    history = _strip_history_citations(build_history(_recent_messages(db, chat_id), settings.chat_history_turns))
    level_code = user.profile.current_level_code if user.profile else (chat.level_code or "")

    # 1) Lưu tin người dùng và commit TRƯỚC khi gọi LLM. KHÔNG refresh ở đây: refresh mở transaction
    #    mới và giữ kết nối DB suốt thời gian chờ LLM (có thể tới LLM_TIMEOUT_SECONDS).
    user_row = ChatMessageRow(session_id=chat_id, language_code=language_code, role="user", content=content)
    db.add(user_row)
    if chat.title is None:
        chat.title = " ".join(content.split())[:TITLE_LENGTH]
    db.commit()

    # 1b) Truy xuất (RAG) — sau commit, không có transaction nào mở. Lỗi hạ tầng (Qdrant, model, chưa có
    #     index) → hạ cấp về llm_only, đánh dấu rag_fallback để giao diện báo người dùng; chat không chết.
    effective_mode, fallback, docs = "llm_only", False, []
    if rag.mode != "llm_only":
        try:
            docs = _retrieve(rag, content, language_code, level_code, settings)
            effective_mode = rag.mode
        except RetrievalError as exc:
            fallback = True
            logger.warning("chat rag_fallback session=%s mode=%s reason=%s", chat_id, rag.mode, exc)
    # B1: ngưỡng tin cậy (tắt mặc định). Điểm dense hạng 1 dưới ngưỡng → trả lời "không thấy trong bài học", không trích dẫn.
    low_confidence = False
    if effective_mode != "llm_only" and settings.rag_min_confidence is not None:
        top = dense_top_score(docs)
        low_confidence = top is None or top < settings.rag_min_confidence
    if low_confidence:
        system_prompt = _low_confidence_prompt(language_code, level_code)
        docs = []
    else:
        system_prompt = _system_prompt(language_code, level_code, docs if effective_mode != "llm_only" else None)

    # 2) Gọi LLM khi không có transaction nào mở. Nội dung người dùng chỉ nằm trong danh sách tin
    #    nhắn, không bao giờ được ghép vào system prompt.
    request = LLMRequest(system_prompt=system_prompt, messages=(*history, ChatMessage("user", content)))
    try:
        result: LLMResult = llm.generate(request)
    except LLMError as error:
        cooldown = llm_cooldown_seconds(error.code, error.retry_after, settings.llm_quota_cooldown_seconds)
        if limits is not None and cooldown is not None:
            # Nhà cung cấp đã báo giới hạn: tạm khóa toàn hệ thống để request kế tiếp bị từ chối sớm
            # bằng `service_busy` thay vì tiếp tục đập vào API (theo phút ≤ 60s; hết hạn mức ngày lâu hơn).
            limits.llm_cooldown.block(cooldown)
        _save_error_turn(db, chat, chat_id, language_code, error.code, model_id=fake_prefix or None,
                         rag_mode=effective_mode, rag_fallback=fallback)
        logger.warning(
            "chat llm_error session=%s code=%s history_messages=%d message_chars=%d",
            chat_id, error.code, len(history), len(content),
        )
        raise llm_error_to_app_error(error) from None
    except Exception as exc:
        # Lỗi ngoài dự kiến (lỗi lập trình, provider ném lỗi lạ): giữ lịch sử nhất quán rồi ném lại để
        # trả 500 theo định dạng lỗi chung. Chỉ log tên lớp lỗi: thông điệp có thể chứa nội dung.
        _save_error_turn(db, chat, chat_id, language_code, INTERNAL_ERROR, model_id=fake_prefix or None,
                         rag_mode=effective_mode, rag_fallback=fallback)
        logger.error(
            "chat internal_error session=%s exc_type=%s history_messages=%d message_chars=%d",
            chat_id, type(exc).__name__, len(history), len(content),
        )
        raise

    # 3) Kiểm tra trích dẫn: chỉ [n] thuộc tập đã truy xuất được giữ; [n] khác bị xóa và ghi lại.
    answer, sources, citations = result.text, None, None
    if effective_mode != "llm_only" and not low_confidence:
        check = check_citations(result.text, len(docs))
        answer = check.text
        citations = {"valid": list(check.valid), "invalid": list(check.invalid)}
        sources = [
            {"n": n, "document_id": d.document_id, "title": d.title, "level": d.level, "rank": d.rank,
             "score": d.score, "text": d.text, "cited": n in check.valid}
            for n, d in enumerate(docs, start=1)
        ]

    # 4) Lưu trả lời kèm metadata (model, token, độ trễ, bị cắt, chế độ RAG, nguồn).
    assistant_row = ChatMessageRow(
        session_id=chat_id,
        language_code=language_code,
        role="assistant",
        content=answer,
        rag_mode=effective_mode,
        rag_fallback=fallback,
        rag_low_confidence=low_confidence,
        sources=sources,
        citations=citations,
        model_id=f"{fake_prefix}{result.model}",  # `fake:` = câu trả lời giả lập, không tốn hạn mức
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        latency_ms=result.latency_ms,
        truncated=result.truncated,
    )
    db.add(assistant_row)
    chat.updated_at = _now_marker()
    db.commit()
    db.refresh(user_row)  # nạp giá trị do DB sinh (created_at) — SAU khi đã có trả lời
    db.refresh(assistant_row)
    logger.info(
        "chat ok session=%s history_messages=%d message_chars=%d reply_chars=%d latency_ms=%d "
        "in_tokens=%s out_tokens=%s truncated=%s rag_mode=%s rag_fallback=%s low_confidence=%s rewrite=%s sources=%d "
        "citations_valid=%d citations_invalid=%d",
        chat_id, len(history), len(content), len(result.text), result.latency_ms,
        result.input_tokens, result.output_tokens, result.truncated, effective_mode, fallback, low_confidence, rag.rewrite_status, len(docs),
        len(citations["valid"]) if citations else 0, len(citations["invalid"]) if citations else 0,
    )
    return user_row, assistant_row


def _save_error_turn(
    db: Session, chat: ChatSession, chat_id: uuid.UUID, language_code: str, code: str, *, model_id: str | None = None,
    rag_mode: str | None = None, rag_fallback: bool = False,
) -> None:
    db.add(
        ChatMessageRow(
            session_id=chat_id, language_code=language_code, role="assistant",
            content="", status="error", error_code=code, model_id=model_id,
            rag_mode=rag_mode, rag_fallback=rag_fallback,
        )
    )
    chat.updated_at = _now_marker()
    db.commit()


def _now_marker():
    # clock_timestamp(): thời điểm thật lúc ghi (now() sẽ trả thời điểm bắt đầu transaction).
    return func.clock_timestamp()
