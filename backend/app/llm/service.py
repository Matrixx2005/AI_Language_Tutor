"""LLMService: lớp dùng chung để gọi LLM, không chứa chuỗi riêng của nhà cung cấp nào.

Tối ưu cho hạn mức gói miễn phí:
- Thử lại ÍT (mặc định 1 lần) và chỉ cho lỗi tạm thời; lỗi người dùng/nội dung không thử lại.
- Tôn trọng `retry_after` của nhà cung cấp; nếu phải chờ lâu hơn `max_wait_seconds` thì không chờ.
- Hết hạn mức/giới hạn ở model chính → chuyển sang model dự phòng (mỗi model thường có hạn mức riêng).
"""
from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from dataclasses import replace

from pydantic import ValidationError

from app.llm.errors import LLMConfigError, LLMError, LLMInvalidResponseError, LLMTimeoutError
from app.llm.provider import LLMProvider
from app.llm.types import LLMRequest, LLMResult, ProviderResponse

logger = logging.getLogger("app.llm")

# Dùng chung cho mọi service: giới hạn số lời gọi LLM chạy song song trong một tiến trình.
_EXECUTOR = ThreadPoolExecutor(max_workers=8, thread_name_prefix="llm")


class LLMService:
    def __init__(
        self,
        provider: LLMProvider,
        *,
        model: str,
        fallback_models: Sequence[str] = (),
        timeout_seconds: float = 30.0,
        max_retries: int = 1,
        backoff_base_seconds: float = 1.0,
        max_wait_seconds: float = 8.0,
        default_max_output_tokens: int | None = None,
        sleep: Callable[[float], None] = time.sleep,
        rng: random.Random | None = None,
    ) -> None:
        if not model:
            raise LLMConfigError("thiếu model ID")
        if max_retries < 0 or timeout_seconds <= 0:
            raise LLMConfigError("max_retries >= 0 và timeout_seconds > 0")
        self.provider = provider
        self.models: tuple[str, ...] = tuple(dict.fromkeys([model, *fallback_models]))  # bỏ trùng
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_base_seconds = backoff_base_seconds
        self.max_wait_seconds = max_wait_seconds
        self.default_max_output_tokens = default_max_output_tokens
        self._sleep = sleep
        self._rng = rng or random.Random()

    def __repr__(self) -> str:
        return f"LLMService(provider={self.provider!r}, models={self.models}, max_retries={self.max_retries})"

    # ------------------------------------------------------------------ public

    def generate(self, request: LLMRequest) -> LLMResult:
        if request.max_output_tokens is None and self.default_max_output_tokens is not None:
            # Giới hạn độ dài trả lời mặc định: tiết kiệm token/hạn mức.
            request = replace(request, max_output_tokens=self.default_max_output_tokens)
        started = time.perf_counter()
        attempts = 0
        last_error: LLMError | None = None

        for index, model in enumerate(self.models):
            for retry in range(self.max_retries + 1):
                attempts += 1
                try:
                    response = self._call_once(request, model)
                    result = self._build_result(request, response, model, index, attempts, started)
                    logger.info(
                        "llm ok model=%s attempts=%d latency_ms=%d in_tokens=%s out_tokens=%s fallback=%s truncated=%s",
                        result.model, attempts, result.latency_ms,
                        result.input_tokens, result.output_tokens, result.fallback_used, result.truncated,
                    )
                    return result
                except LLMError as error:
                    last_error = error
                    logger.warning("llm error code=%s model=%s attempt=%d", error.code, model, attempts)
                    if not error.retryable or retry == self.max_retries:
                        break
                    wait = self._wait_before_retry(error, retry)
                    if wait is None:  # nhà cung cấp bảo chờ quá lâu → bỏ cùng model
                        break
                    self._sleep(wait)
            if last_error is None or not last_error.fallback_allowed:
                break  # lỗi không liên quan đến model (nội dung bị chặn, sai định dạng...)

        assert last_error is not None
        raise last_error

    # ----------------------------------------------------------------- private

    def _call_once(self, request: LLMRequest, model: str) -> ProviderResponse:
        # Provider nhận timeout để tự hủy kết nối; future.result là chốt chặn cuối nếu provider treo.
        future = _EXECUTOR.submit(
            self.provider.generate, request, model=model, timeout_seconds=self.timeout_seconds
        )
        try:
            return future.result(timeout=self.timeout_seconds)
        except FutureTimeoutError:
            future.cancel()
            raise LLMTimeoutError(f"quá {self.timeout_seconds}s") from None
        except LLMError:
            raise
        except Exception as exc:  # provider ném lỗi lạ: không để lộ ra ngoài
            raise LLMInvalidResponseError(f"lỗi không chuẩn hóa: {type(exc).__name__}") from exc

    def _build_result(
        self,
        request: LLMRequest,
        response: ProviderResponse,
        model: str,
        model_index: int,
        attempts: int,
        started: float,
    ) -> LLMResult:
        if not response.text or not response.text.strip():
            raise LLMInvalidResponseError("phản hồi rỗng")
        parsed = None
        if request.response_schema is not None:
            try:
                parsed = request.response_schema.model_validate_json(response.text)
            except ValidationError as exc:
                raise LLMInvalidResponseError(f"không khớp schema ({exc.error_count()} lỗi)") from None
        return LLMResult(
            text=response.text,
            model=response.model or model,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            latency_ms=round((time.perf_counter() - started) * 1000),
            attempts=attempts,
            parsed=parsed,
            fallback_used=model_index > 0,
            requested_model=self.models[0],
            truncated=response.truncated,
        )

    def _wait_before_retry(self, error: LLMError, retry: int) -> float | None:
        if error.retry_after is not None:
            return error.retry_after if error.retry_after <= self.max_wait_seconds else None
        # Exponential backoff + jitter: base * 2^retry, nhân ngẫu nhiên 50–100%, tối đa max_wait.
        delay = min(self.max_wait_seconds, self.backoff_base_seconds * (2**retry))
        return delay * (0.5 + self._rng.random() / 2)
