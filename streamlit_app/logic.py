"""Hàm thuần cho Streamlit console (không import streamlit) — có pytest trong backend/tests/test_streamlit_logic.py.

Streamlit là lớp mỏng: KHÔNG chứa nghiệp vụ (chấm điểm, giới hạn, RAG...). Ở đây chỉ có ánh xạ lỗi để hiển thị,
định dạng thời gian chờ, cổng mã truy cập, chế độ công khai, lọc dev-only và hiển thị văn bản thuần.
"""
from __future__ import annotations

import hmac
import math
import os
import re
from collections.abc import Iterable, Mapping

DEFAULT_API_BASE_URL = "http://127.0.0.1:8000/api/v1"

# Giống frontend/src/lib/apiErrors.ts (chỉ thông điệp hiển thị).
MESSAGES: dict[str, str] = {
    "chat_rate_limited": "Bạn đang gửi tin hơi nhanh.",
    "chat_daily_limit_reached": "Bạn đã dùng hết lượt hỏi gia sư AI hôm nay.",
    "chat_busy": "Gia sư AI đang trả lời tin trước của bạn.",
    "service_busy": "Hệ thống đang bận.",
    "auth_rate_limited": "Bạn đã thử quá nhiều lần.",
    "llm_timeout": "Gia sư AI phản hồi quá lâu nên chưa trả lời được.",
    "llm_provider_error": "Gia sư AI tạm thời không phản hồi.",
    "llm_invalid_response": "Gia sư AI trả lời không hợp lệ.",
    "llm_content_blocked": "Nội dung này không thể xử lý. Hãy diễn đạt câu hỏi theo cách khác.",
    "llm_not_configured": "Gia sư AI chưa được cấu hình trên máy chủ.",
    "llm_rate_limited": "Gia sư AI đang quá tải.",
    "llm_quota_exhausted": "Gia sư AI đã hết lượt dùng trong hôm nay.",
    "internal_error": "Đã có lỗi ngoài dự kiến.",
    "network_error": "Không kết nối được backend. Hãy kiểm tra uvicorn đã chạy chưa (xem README).",
    "invalid_credentials": "Email hoặc mật khẩu không đúng.",
    "not_authenticated": "Bạn cần đăng nhập.",
    "token_expired": "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.",
    "invalid_token": "Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.",
    "chat_session_not_found": "Không tìm thấy cuộc trò chuyện.",
    "placement_not_available": "Chưa có bài kiểm tra đầu vào cho ngôn ngữ của bạn.",
    "placement_already_submitted": "Bài kiểm tra này đã được nộp.",
    "placement_questions_changed": "Bộ câu hỏi vừa được cập nhật nên bài làm dở không còn dùng được.",
    "placement_superseded": "Đã có kết quả mới hơn.",
    "placement_not_completed": "Hãy nộp bài trước khi cập nhật trình độ.",
    "placement_not_found": "Không tìm thấy bài kiểm tra.",
}
LIMIT_CODES = {"chat_rate_limited", "chat_daily_limit_reached", "chat_busy", "service_busy", "auth_rate_limited",
               "llm_rate_limited", "llm_quota_exhausted"}


def message_for_code(code: str | None, server_message: str | None = None) -> str:
    if code and code in MESSAGES:
        return MESSAGES[code]
    return server_message or "Yêu cầu chưa thành công. Vui lòng thử lại."


def parse_retry_after(value: str | None) -> int | None:
    """Chỉ nhận số giây nguyên không âm (backend luôn gửi dạng này)."""
    if value is None or not value.strip().isdigit():
        return None
    return int(value.strip())


def format_wait(seconds: float) -> str:
    s = max(0, math.ceil(seconds))
    if s < 60:
        return f"{s} giây"
    if s < 3600:
        m, r = divmod(s, 60)
        return f"{m} phút {r} giây" if r else f"{m} phút"
    h, rest = divmod(s, 3600)
    m = math.ceil(rest / 60)
    if m == 60:
        return f"{h + 1} giờ"
    return f"{h} giờ {m} phút" if m else f"{h} giờ"


def seconds_left(until: float | None, now: float) -> int:
    return 0 if until is None else max(0, math.ceil(until - now))


# ---------- Chia sẻ an toàn ----------


def access_code_required(env: Mapping[str, str] | None = None) -> bool:
    env = os.environ if env is None else env
    return bool(env.get("STREAMLIT_ACCESS_CODE", "").strip())


def check_access_code(entered: str, env: Mapping[str, str] | None = None) -> bool:
    """So sánh hằng thời gian. Không đặt mã → không cần cổng (trả True)."""
    env = os.environ if env is None else env
    expected = env.get("STREAMLIT_ACCESS_CODE", "").strip()
    if not expected:
        return True
    return hmac.compare_digest(entered.strip().encode("utf-8"), expected.encode("utf-8"))


def public_mode(env: Mapping[str, str] | None = None) -> bool:
    env = os.environ if env is None else env
    return env.get("STREAMLIT_PUBLIC_MODE", "").strip().lower() in {"1", "true", "yes", "on"}


def chat_allowed(is_public: bool, llm_provider: str | None) -> tuple[bool, str]:
    """Chế độ công khai chỉ cho phép backend chạy LLM_PROVIDER=fake (không tốn hạn mức Gemini của chủ dự án)."""
    if not is_public:
        return True, ""
    if llm_provider == "fake":
        return True, ""
    if llm_provider is None:
        return False, "Chế độ công khai: không xác định được nhà cung cấp LLM của backend nên tạm chặn chat."
    return False, (f"Chế độ công khai đang bật nhưng backend dùng LLM_PROVIDER={llm_provider}. "
                   "Chat bị chặn để không tiêu hạn mức Gemini; hãy chạy backend với LLM_PROVIDER=fake.")


def api_base_url(env: Mapping[str, str] | None = None) -> str:
    env = os.environ if env is None else env
    return (env.get("STREAMLIT_API_BASE_URL") or DEFAULT_API_BASE_URL).rstrip("/")


# ---------- Dữ liệu đánh giá: chỉ DEV ----------


def dev_only(queries: Iterable[Mapping]) -> list[dict]:
    """Chỉ truy vấn split == 'dev' (so khớp chính xác). Test split không bao giờ đi qua đây ra giao diện."""
    return [dict(q) for q in queries if q.get("split") == "dev"]


# ---------- Hiển thị văn bản thuần ----------

_MD_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+\-.!|<>~$])")


def plain_markdown(text: str) -> str:
    """Biến văn bản (có thể do LLM viết) thành markdown hiển thị NGUYÊN VĂN: escape mọi ký tự markdown/HTML,
    giữ xuống dòng. Dùng với st.markdown (không bao giờ unsafe_allow_html)."""
    escaped = _MD_SPECIAL.sub(r"\\\1", text)
    return escaped.replace("\n", "  \n")


# ---------- Corpus ----------


def parse_review_status(markdown: str) -> dict[str, str]:
    """Đọc cột trạng thái trong docs/CORPUS_REVIEW.md: document_id → trạng thái."""
    status = {}
    for line in markdown.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 7 and cells[1].startswith("`gram-"):
            status[cells[1].strip("`")] = cells[6].replace("**", "")
    return status


# ---------- Bài tập (Tuần 5B) ----------

RULE_GRADED_TYPES = ("mcq", "cloze", "reorder")
ALL_EXERCISE_TYPES = ("mcq", "cloze", "error_correction", "reorder", "translate_vi_en")
EXERCISE_TYPE_LABELS = {"mcq": "Trắc nghiệm", "cloze": "Điền từ", "error_correction": "Sửa lỗi",
                        "reorder": "Sắp xếp câu", "translate_vi_en": "Dịch Việt → Anh"}


def exercise_types_allowed(is_public: bool, llm_provider: str | None) -> tuple[str, ...]:
    """Chế độ công khai + backend dùng Gemini: chỉ dạng chấm bằng quy tắc (không tốn lượt LLM).
    Sửa lỗi/dịch có thể cần LLM chấm nên bị ẩn."""
    if is_public and llm_provider != "fake":
        return RULE_GRADED_TYPES
    return ALL_EXERCISE_TYPES


def admin_page_enabled(env=None) -> bool:
    """Trang duyệt bài chỉ hiện khi đã đặt mã truy cập (không để lộ khi chia sẻ link không có mã)."""
    return access_code_required(env)
