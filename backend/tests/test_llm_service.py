"""LLMService với FakeLLM: không mạng, không key, không sleep thật."""
import logging
import random
import time
from pathlib import Path

import pytest
from pydantic import BaseModel

from app.core.config import Settings
from app.llm import build_llm_service
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
from app.llm.fake import Delay, Fail, FakeLLM, Reply
from app.llm.service import LLMService
from app.llm.types import ChatMessage, LLMRequest

SECRET_CONTENT = "noi-dung-rieng-tu-cua-nguoi-hoc-123"
REQUEST = LLMRequest(
    system_prompt="Bạn là gia sư.",
    messages=(ChatMessage("user", SECRET_CONTENT),),
)


class Sleeps(list):
    def __call__(self, seconds: float) -> None:
        self.append(seconds)


def make_service(*steps, max_retries=1, fallback=(), timeout=5.0, **kwargs):
    provider = FakeLLM(steps)
    sleeps = Sleeps()
    service = LLMService(
        provider,
        model="model-chinh",
        fallback_models=fallback,
        timeout_seconds=timeout,
        max_retries=max_retries,
        sleep=sleeps,
        rng=random.Random(0),
        **kwargs,
    )
    return service, provider, sleeps


# ---------- Thành công ----------


def test_success_returns_text_model_tokens_latency():
    service, provider, sleeps = make_service(Reply("Xin chào", input_tokens=7, output_tokens=3))

    result = service.generate(REQUEST)

    assert (result.text, result.model, result.input_tokens, result.output_tokens) == ("Xin chào", "model-chinh", 7, 3)
    assert result.attempts == 1 and len(provider.calls) == 1 and sleeps == []
    assert result.latency_ms >= 0 and not result.fallback_used
    assert provider.calls[0].request is REQUEST  # system prompt và tin nhắn được truyền nguyên vẹn


def test_truncated_flag_is_propagated():
    service, _, _ = make_service(Reply("dở dang", truncated=True))
    assert service.generate(REQUEST).truncated is True


def test_normal_reply_is_not_truncated():
    service, _, _ = make_service(Reply("đầy đủ"))
    assert service.generate(REQUEST).truncated is False


def test_provider_response_repr_hides_content():
    from app.llm.types import ProviderResponse

    response = ProviderResponse(text=SECRET_CONTENT, model="m", truncated=True)
    assert SECRET_CONTENT not in repr(response) and "truncated=True" in repr(response)


def test_reports_model_actually_used_by_provider():
    service, _, _ = make_service(Reply("ok", model="model-chinh-002"))
    assert service.generate(REQUEST).model == "model-chinh-002"


# ---------- Thử lại ----------


@pytest.mark.parametrize("error", [LLMTimeoutError(), LLMRateLimitError(), LLMProviderError()])
def test_transient_error_is_retried_then_succeeds(error):
    service, provider, sleeps = make_service(Fail(error), Reply("ok"))

    result = service.generate(REQUEST)

    assert result.text == "ok" and result.attempts == 2 and len(provider.calls) == 2
    assert len(sleeps) == 1 and 0.5 <= sleeps[0] <= 1.0  # backoff 1s * jitter 50–100%


def test_retries_are_bounded():
    service, provider, sleeps = make_service(*[Fail(LLMProviderError())] * 10, max_retries=2)

    with pytest.raises(LLMProviderError):
        service.generate(REQUEST)

    assert len(provider.calls) == 3  # 1 lần đầu + 2 lần thử lại, không hơn
    assert len(sleeps) == 2 and sleeps[1] > sleeps[0] * 0.9  # tăng dần (có jitter)


def test_zero_retries_calls_once():
    service, provider, _ = make_service(Fail(LLMProviderError()), Reply("ok"), max_retries=0)
    with pytest.raises(LLMProviderError):
        service.generate(REQUEST)
    assert len(provider.calls) == 1


@pytest.mark.parametrize(
    "error", [LLMContentBlockedError(), LLMInvalidResponseError(), LLMConfigError(), LLMQuotaExhaustedError()]
)
def test_non_transient_errors_are_not_retried(error):
    service, provider, sleeps = make_service(Fail(error), Reply("ok"), max_retries=3)

    with pytest.raises(type(error)):
        service.generate(REQUEST)

    assert len(provider.calls) == 1 and sleeps == []


def test_retry_after_is_respected_when_short():
    service, _, sleeps = make_service(Fail(LLMRateLimitError(retry_after=3.0)), Reply("ok"))
    service.generate(REQUEST)
    assert sleeps == [3.0]


def test_long_retry_after_is_not_waited_for():
    service, provider, sleeps = make_service(Fail(LLMRateLimitError(retry_after=60.0)), Reply("ok"), max_retries=3)

    with pytest.raises(LLMRateLimitError) as caught:
        service.generate(REQUEST)

    assert sleeps == [] and len(provider.calls) == 1
    assert caught.value.retry_after == 60.0  # để API báo cho người dùng thời gian chờ


# ---------- Timeout ----------


def test_slow_provider_times_out_quickly():
    service, provider, _ = make_service(Delay(2.0), max_retries=0, timeout=0.2)

    started = time.perf_counter()
    with pytest.raises(LLMTimeoutError):
        service.generate(REQUEST)

    assert time.perf_counter() - started < 1.0  # không chờ hết 2 giây
    assert provider.calls[0].timeout_seconds == 0.2  # provider nhận timeout để tự hủy kết nối


def test_timeout_is_retried_once():
    service, provider, _ = make_service(Delay(1.0), Reply("ok"), max_retries=1, timeout=0.2)
    assert service.generate(REQUEST).text == "ok"
    assert len(provider.calls) == 2


# ---------- Model dự phòng ----------


@pytest.mark.parametrize("error", [LLMQuotaExhaustedError(), LLMRateLimitError(retry_after=999)])
def test_falls_back_to_next_model_when_quota_or_limit_hit(error):
    service, provider, _ = make_service(Fail(error), Reply("ok"), fallback=("model-du-phong",), max_retries=1)

    result = service.generate(REQUEST)

    assert result.model == "model-du-phong" and result.fallback_used
    assert result.requested_model == "model-chinh"
    assert [call.model for call in provider.calls] == ["model-chinh", "model-du-phong"]


def test_blocked_content_does_not_try_fallback_model():
    service, provider, _ = make_service(Fail(LLMContentBlockedError()), Reply("ok"), fallback=("model-du-phong",))
    with pytest.raises(LLMContentBlockedError):
        service.generate(REQUEST)
    assert [call.model for call in provider.calls] == ["model-chinh"]


def test_all_models_exhausted_raises_last_error():
    service, provider, _ = make_service(
        Fail(LLMQuotaExhaustedError()), Fail(LLMQuotaExhaustedError()), fallback=("model-du-phong",)
    )
    with pytest.raises(LLMQuotaExhaustedError):
        service.generate(REQUEST)
    assert len(provider.calls) == 2


def test_duplicate_fallback_model_is_ignored():
    service, _, _ = make_service(fallback=("model-chinh", "model-du-phong"))
    assert service.models == ("model-chinh", "model-du-phong")


# ---------- Structured output ----------


class Verdict(BaseModel):
    level_code: str
    confidence: float


def test_structured_output_valid_json_is_parsed():
    service, _, _ = make_service(Reply('{"level_code": "A2", "confidence": 0.8}'))

    result = service.generate(LLMRequest("s", REQUEST.messages, response_schema=Verdict))

    assert isinstance(result.parsed, Verdict) and result.parsed.level_code == "A2"


@pytest.mark.parametrize("text", ["không phải json", '{"level_code": "A2"}', '{"level_code": 1, "confidence": "x"}'])
def test_structured_output_invalid_raises_without_retry(text):
    service, provider, _ = make_service(Reply(text), Reply('{"level_code": "A2", "confidence": 1}'), max_retries=2)

    with pytest.raises(LLMInvalidResponseError):
        service.generate(LLMRequest("s", REQUEST.messages, response_schema=Verdict))

    assert len(provider.calls) == 1


@pytest.mark.parametrize("text", ["", "   \n"])
def test_empty_reply_is_invalid(text):
    service, _, _ = make_service(Reply(text), max_retries=0)
    with pytest.raises(LLMInvalidResponseError):
        service.generate(REQUEST)


def test_unexpected_provider_exception_is_normalized():
    class Broken(FakeLLM):
        def generate(self, request, *, model, timeout_seconds):
            raise KeyError("chi-tiet-noi-bo")

    service = LLMService(Broken(), model="m", max_retries=0)
    with pytest.raises(LLMInvalidResponseError) as caught:
        service.generate(REQUEST)
    assert isinstance(caught.value, LLMError) and "chi-tiet-noi-bo" not in caught.value.code


# ---------- Không rò nội dung/secret ----------


def test_logs_and_reprs_contain_metadata_not_content(caplog):
    caplog.set_level(logging.DEBUG, logger="app.llm")
    service, _, _ = make_service(Fail(LLMProviderError()), Reply(f"trả lời {SECRET_CONTENT}"))

    result = service.generate(REQUEST)

    assert "llm ok model=model-chinh attempts=2" in caplog.text
    assert "llm error code=llm_provider_error" in caplog.text
    for text in (caplog.text, repr(REQUEST), repr(result), repr(REQUEST.messages[0]), repr(service)):
        assert SECRET_CONTENT not in text


def test_shared_llm_modules_contain_no_provider_specific_strings():
    """Chỉ danh bạ providers.py (và module của từng nhà cung cấp) được biết tên nhà cung cấp."""
    llm_dir = Path(__file__).resolve().parents[1] / "app" / "llm"
    for name in ("service.py", "provider.py", "types.py", "errors.py", "__init__.py"):
        source = (llm_dir / name).read_text(encoding="utf-8").lower()
        for vendor in ("gemini", "google", "openai", "anthropic", "genai"):
            assert vendor not in source, f"{name} chứa '{vendor}'"


# ---------- Cấu hình ----------


def test_build_from_settings_with_fake_provider():
    settings = Settings(
        _env_file=None,
        llm_provider="fake",
        llm_fallback_model_ids=" a , b ,",
        llm_timeout_seconds=12,
        llm_max_retries=2,
    )

    service = build_llm_service(settings)

    assert service.models == ("fake-model", "a", "b")
    assert (service.timeout_seconds, service.max_retries) == (12, 2)
    assert service.generate(REQUEST).text  # FakeLLM mặc định trả lời được


def test_unknown_provider_is_config_error():
    with pytest.raises(LLMConfigError):
        build_llm_service(Settings(_env_file=None, llm_provider="khong-ton-tai"))


def test_provider_without_default_model_requires_model_id():
    with pytest.raises(LLMConfigError):
        LLMService(FakeLLM(), model="")


def test_safe_defaults_use_fake_provider_and_few_retries():
    settings = Settings(_env_file=None)
    assert settings.llm_provider == "fake"
    assert settings.llm_max_retries == 1
