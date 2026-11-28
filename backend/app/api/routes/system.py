"""Trạng thái hệ thống cho bảng điều khiển (Streamlit, Tuần 5A). Chỉ thông tin KHÔNG bí mật:
nhà cung cấp LLM (fake|gemini), chế độ RAG, các giới hạn đang áp dụng, DB/Qdrant có hoạt động không.
Không bao giờ trả key, mật khẩu, JWT secret, chuỗi kết nối hay URL nội bộ."""
from __future__ import annotations

import urllib.request

from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import DbSession
from app.core.config import get_settings

router = APIRouter(prefix="/system", tags=["system"])


def _qdrant_ok(url: str, timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(f"{url.rstrip('/')}/readyz", timeout=timeout) as response:  # noqa: S310 (URL cấu hình nội bộ)
            return response.status == 200
    except Exception:
        return False


@router.get("/status")
def system_status(db: DbSession) -> dict:
    settings = get_settings()
    try:
        db.execute(text("SELECT 1"))
        database = "ok"
    except Exception:
        database = "error"
    rag_used = settings.rag_mode != "llm_only"
    return {
        "llm_provider": settings.llm_provider,
        "rag_mode": settings.rag_mode,
        "rag_top_k": settings.rag_top_k,
        "database": database,
        "qdrant": "ok" if _qdrant_ok(settings.qdrant_url) else ("error" if rag_used else "unavailable"),
        "limits": {
            "chat_max_message_chars": settings.chat_max_message_chars,
            "chat_user_per_minute": settings.chat_user_per_minute,
            "chat_user_per_day": settings.chat_user_per_day,
            "llm_global_per_minute": settings.llm_global_per_minute,
            "llm_global_per_day": settings.llm_global_per_day,
            "auth_login_fails_per_email": settings.auth_login_fails_per_email,
            "auth_login_window_seconds": settings.auth_login_window_seconds,
        },
    }
