"""Lỗi LLM chuẩn hóa, không phụ thuộc nhà cung cấp.

Mỗi lỗi có `code` ổn định (frontend dùng), `retryable` (thử lại cùng model có ích không) và
`fallback_allowed` (chuyển sang model dự phòng có ích không). Thông điệp KHÔNG chứa chi tiết
nội bộ của nhà cung cấp, prompt hay nội dung người dùng.
"""
from __future__ import annotations


class LLMError(Exception):
    code = "llm_error"
    retryable = False
    fallback_allowed = False

    def __init__(self, detail: str = "", *, retry_after: float | None = None) -> None:
        # `detail` chỉ dùng cho log nội bộ; không trả cho người dùng.
        super().__init__(detail or self.code)
        self.detail = detail
        self.retry_after = retry_after


class LLMTimeoutError(LLMError):
    code = "llm_timeout"
    retryable = True


class LLMRateLimitError(LLMError):
    """Giới hạn tần suất tạm thời (ví dụ RPM). Thử lại sau `retry_after` có thể thành công."""

    code = "llm_rate_limited"
    retryable = True
    fallback_allowed = True


class LLMQuotaExhaustedError(LLMError):
    """Hết hạn mức (ví dụ RPD của gói miễn phí): thử lại cùng model vô ích, model khác có thể còn."""

    code = "llm_quota_exhausted"
    fallback_allowed = True


class LLMContentBlockedError(LLMError):
    code = "llm_content_blocked"


class LLMInvalidResponseError(LLMError):
    """Phản hồi rỗng, sai định dạng hoặc không khớp schema structured output."""

    code = "llm_invalid_response"


class LLMProviderError(LLMError):
    """Lỗi phía máy chủ nhà cung cấp (5xx, mất kết nối)."""

    code = "llm_provider_error"
    retryable = True
    fallback_allowed = True


class LLMConfigError(LLMError):
    """Cấu hình thiếu/sai (chưa có key, model ID, provider lạ). Không thử lại."""

    code = "llm_not_configured"
