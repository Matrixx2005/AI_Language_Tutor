"""Nhà cung cấp Gemini (SDK chính thức google-genai). Module DUY NHẤT đọc GEMINI_API_KEY.

Đã đối chiếu mã nguồn google-genai 3.6.1 (không dựa vào trí nhớ):
- `HttpOptions.timeout` tính bằng MILI GIÂY; SDK truyền xuống httpx và header X-Server-Timeout.
- Không truyền `retry_options` thì SDK không tự thử lại; vẫn đặt `attempts=1` tường minh để
  LLMService là nơi duy nhất quyết định thử lại (tránh thử lại chồng hai tầng, tốn hạn mức).
- Key được gửi qua header `x-goog-api-key` (không nằm trong URL bị httpx log).
- Lỗi HTTP: `errors.ClientError` (4xx), `errors.ServerError` (5xx), cùng gốc `errors.APIError`
  có `.code`, `.status`, `.details` (JSON lỗi gốc).
"""
from __future__ import annotations

import re
from typing import Any

import httpx2
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.config import PROJECT_ROOT
from app.llm.errors import (
    LLMConfigError,
    LLMContentBlockedError,
    LLMError,
    LLMInvalidResponseError,
    LLMProviderError,
    LLMQuotaExhaustedError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from app.llm.provider import LLMProvider
from app.llm.types import LLMRequest, ProviderResponse

# finish_reason / block_reason coi là "nội dung bị chặn" (types.FinishReason, types.BlockedReason).
_BLOCKED_FINISH_REASONS = {"SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT", "SPII", "LANGUAGE"}
_ROLE = {"user": "user", "assistant": "model"}
_THINKING_LEVELS = {"minimal", "low", "medium", "high"}
_RETRY_DELAY = re.compile(r"^\s*(\d+(?:\.\d+)?)s\s*$")


class GeminiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore")

    gemini_api_key: SecretStr | None = None
    # Mức "suy nghĩ" (docs/thinking): gemini-3.8-flash mặc định `medium` → chậm và tốn token
    # (token suy nghĩ tính vào max_output_tokens và chi phí). `low` được cả 3.8-flash lẫn
    # 3.5-flash-lite hỗ trợ; `minimal` KHÔNG hỗ trợ trên 3.8-flash. Để trống = mặc định của model.
    gemini_thinking_level: str = "low"

    @field_validator("gemini_thinking_level")
    @classmethod
    def _valid_level(cls, value: str) -> str:
        value = value.strip().lower()
        if value and value not in _THINKING_LEVELS:
            raise ValueError(f"GEMINI_THINKING_LEVEL phải là một trong {sorted(_THINKING_LEVELS)} hoặc để trống")
        return value


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(
        self,
        api_key: SecretStr | None,
        *,
        thinking_level: str = "low",
        http_client: httpx2.Client | None = None,
    ) -> None:
        if api_key is None or not api_key.get_secret_value().strip():
            raise LLMConfigError("GEMINI_API_KEY chưa được đặt trong .env")
        self._thinking = (
            types.ThinkingConfig(thinking_level=types.ThinkingLevel(thinking_level.upper()))
            if thinking_level
            else None
        )
        # Chỉ giữ client SDK; không lưu key ở thuộc tính riêng để tránh lộ qua repr/vars().
        options = types.HttpOptions(
            retry_options=types.HttpRetryOptions(attempts=1),
            httpx_client=http_client,
        )
        self._client = genai.Client(api_key=api_key.get_secret_value().strip(), http_options=options)

    def __repr__(self) -> str:
        return "GeminiProvider()"

    # ------------------------------------------------------------------ gọi API

    def generate(self, request: LLMRequest, *, model: str, timeout_seconds: float) -> ProviderResponse:
        structured: dict[str, Any] = {}
        if request.response_schema is not None:
            structured = {"response_mime_type": "application/json", "response_schema": request.response_schema}
        config = types.GenerateContentConfig(
            system_instruction=request.system_prompt,
            max_output_tokens=request.max_output_tokens,
            thinking_config=self._thinking,
            http_options=types.HttpOptions(
                timeout=max(1, round(timeout_seconds * 1000)),  # mili giây
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
            **structured,
        )

        contents = [
            types.Content(role=_ROLE[message.role], parts=[types.Part(text=message.content)])
            for message in request.messages
        ]
        try:
            response = self._client.models.generate_content(model=model, contents=contents, config=config)
        except genai_errors.APIError as exc:
            raise _map_api_error(exc) from None  # from None: traceback không mang theo lỗi gốc của SDK
        except httpx2.TimeoutException:
            raise LLMTimeoutError(f"quá {timeout_seconds}s") from None
        except httpx2.TransportError as exc:
            raise LLMProviderError(f"lỗi kết nối: {type(exc).__name__}") from None
        return _to_provider_response(response, model)


# ---------------------------------------------------------------- ánh xạ kết quả


def _to_provider_response(response: types.GenerateContentResponse, requested_model: str) -> ProviderResponse:
    feedback = response.prompt_feedback
    if feedback is not None and feedback.block_reason is not None:
        raise LLMContentBlockedError(f"prompt bị chặn: {_enum_name(feedback.block_reason)}")
    if not response.candidates:
        raise LLMInvalidResponseError("không có candidate")

    candidate = response.candidates[0]
    finish = _enum_name(candidate.finish_reason)
    if finish in _BLOCKED_FINISH_REASONS:
        raise LLMContentBlockedError(f"phản hồi bị chặn: {finish}")

    parts = (candidate.content.parts or []) if candidate.content else []
    text = "".join(part.text for part in parts if part.text and not part.thought)
    if not text.strip():
        raise LLMInvalidResponseError(f"phản hồi không có văn bản (finish_reason={finish})")

    usage = response.usage_metadata
    output_tokens = None
    if usage is not None and usage.candidates_token_count is not None:
        # Token "suy nghĩ" cũng tính vào hạn mức/chi phí đầu ra → cộng vào để đo đúng.
        output_tokens = usage.candidates_token_count + (usage.thoughts_token_count or 0)
    return ProviderResponse(
        text=text,
        model=response.model_version or requested_model,
        input_tokens=usage.prompt_token_count if usage is not None else None,
        output_tokens=output_tokens,
        # Vẫn trả văn bản; structured output bị cắt sẽ hỏng JSON và bị LLMService báo sai định dạng.
        truncated=finish == "MAX_TOKENS",
    )


def _map_api_error(exc: genai_errors.APIError) -> LLMError:
    code = exc.code or 0
    status = str(exc.status or "")
    detail = f"HTTP {code} {status}".strip()  # KHÔNG kèm message/details: có thể chứa dữ liệu yêu cầu
    retry_after = _retry_after_seconds(exc.details)

    if code == 429:
        if _is_daily_quota(exc.details):
            return LLMQuotaExhaustedError(detail, retry_after=retry_after)
        return LLMRateLimitError(detail, retry_after=retry_after)
    if code == 402:  # hết số dư trả trước
        return LLMQuotaExhaustedError(detail)
    if code in (400, 401, 403, 404):  # sai key, không có quyền, model không tồn tại, tham số sai
        return LLMConfigError(detail)
    if code in (408, 504):
        return LLMTimeoutError(detail)
    if code >= 500:
        return LLMProviderError(detail)
    return LLMInvalidResponseError(detail)


def _error_details(details: Any) -> list[dict]:
    """JSON lỗi Google: {"error": {"details": [{"@type": ...}, ...]}}."""
    if isinstance(details, dict):
        inner = details.get("error", details)
        items = inner.get("details") if isinstance(inner, dict) else None
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
    return []


def _retry_after_seconds(details: Any) -> float | None:
    for item in _error_details(details):
        if str(item.get("@type", "")).endswith("google.rpc.RetryInfo"):
            match = _RETRY_DELAY.match(str(item.get("retryDelay", "")))
            if match:
                return float(match.group(1))
    return None


def _is_daily_quota(details: Any) -> bool:
    """Phân biệt hết hạn mức NGÀY (thử lại vô ích) với giới hạn theo phút (chờ là được)."""
    for item in _error_details(details):
        if str(item.get("@type", "")).endswith("google.rpc.QuotaFailure"):
            for violation in item.get("violations") or []:
                if isinstance(violation, dict) and "perday" in str(violation.get("quotaId", "")).lower():
                    return True
    return False


def _enum_name(value: Any) -> str:
    if value is None:
        return ""
    return str(getattr(value, "value", None) or getattr(value, "name", None) or value).upper()


def create_gemini_provider() -> GeminiProvider:
    settings = GeminiSettings()
    return GeminiProvider(settings.gemini_api_key, thinking_level=settings.gemini_thinking_level)
