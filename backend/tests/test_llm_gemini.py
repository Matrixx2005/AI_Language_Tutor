"""GeminiProvider chạy qua code thật của SDK google-genai, nhưng HTTP bị thay bằng
httpx2.MockTransport: không mạng, không key thật.
"""
import json
import logging
import traceback

import httpx2
import pytest
from pydantic import BaseModel, SecretStr

from app.core.config import Settings
from app.llm import build_llm_service
from app.llm import gemini as gemini_module
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
from app.llm.gemini import GeminiProvider, GeminiSettings
from app.llm.service import LLMService
from app.llm.types import ChatMessage, LLMRequest

FAKE_KEY = "FAKEKEY-khong-phai-key-that-7f3a9c2e1b"
REQUEST = LLMRequest(
    system_prompt="Bạn là gia sư tiếng Anh.",
    messages=(ChatMessage("user", "Xin chào"), ChatMessage("assistant", "Chào bạn!"), ChatMessage("user", "Thì hiện tại đơn?")),
    max_output_tokens=256,
)


class Recorder:
    """Handler cho MockTransport: trả lần lượt các phản hồi, ghi lại request."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests: list[httpx2.Request] = []

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        item = self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]
        if isinstance(item, Exception):
            raise item
        status, body = item
        return httpx2.Response(status, json=body)


def make_provider(recorder: Recorder) -> GeminiProvider:
    client = httpx2.Client(transport=httpx2.MockTransport(recorder))
    return GeminiProvider(SecretStr(FAKE_KEY), http_client=client)


def ok(text="Câu trả lời", *, finish="STOP", usage=True, model_version="gemini-test-001", parts=None):
    body = {
        "candidates": [{
            "content": {"role": "model", "parts": parts if parts is not None else [{"text": text}]},
            "finishReason": finish,
        }],
    }
    if usage:
        body["usageMetadata"] = {"promptTokenCount": 12, "candidatesTokenCount": 5, "thoughtsTokenCount": 3, "totalTokenCount": 20}
    if model_version:
        body["modelVersion"] = model_version
    return 200, body


def error(code, status, details=()):
    return code, {"error": {"code": code, "status": status, "message": "chi tiết nội bộ từ máy chủ", "details": list(details)}}


QUOTA_PER_DAY = {
    "@type": "type.googleapis.com/google.rpc.QuotaFailure",
    "violations": [{"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}],
}
QUOTA_PER_MINUTE = {
    "@type": "type.googleapis.com/google.rpc.QuotaFailure",
    "violations": [{"quotaId": "GenerateRequestsPerMinutePerProjectPerModel-FreeTier"}],
}


def retry_info(seconds: str):
    return {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": seconds}


# ---------- Thành công và nội dung request ----------


def test_success_maps_text_tokens_and_actual_model():
    recorder = Recorder(ok("Hiện tại đơn dùng cho thói quen."))

    response = make_provider(recorder).generate(REQUEST, model="gemini-test", timeout_seconds=7.5)

    assert response.text == "Hiện tại đơn dùng cho thói quen."
    assert (response.input_tokens, response.output_tokens) == (12, 8)  # 5 trả lời + 3 suy nghĩ
    assert response.model == "gemini-test-001"  # model THỰC TẾ phản hồi


def test_request_shape_key_header_and_timeout():
    recorder = Recorder(ok())

    make_provider(recorder).generate(REQUEST, model="gemini-test", timeout_seconds=7.5)

    (request,) = recorder.requests
    body = json.loads(request.content)
    assert request.url.path.endswith("/models/gemini-test:generateContent")
    assert request.headers["x-goog-api-key"] == FAKE_KEY  # key đi trong header...
    assert FAKE_KEY not in str(request.url)  # ...không nằm trong URL (URL bị httpx log)
    assert body["systemInstruction"]["parts"][0]["text"] == "Bạn là gia sư tiếng Anh."
    assert [content["role"] for content in body["contents"]] == ["user", "model", "user"]
    assert body["generationConfig"]["maxOutputTokens"] == 256
    # Timeout được truyền xuống tầng HTTP (không chạy nền vô hạn khi LLMService đã bỏ cuộc).
    assert request.extensions["timeout"]["read"] == pytest.approx(7.5)
    assert request.headers.get("x-server-timeout") == "8"


def test_thinking_level_defaults_to_low_and_is_sent():
    recorder = Recorder(ok())
    make_provider(recorder).generate(REQUEST, model="m", timeout_seconds=5)
    thinking = json.loads(recorder.requests[0].content)["generationConfig"]["thinkingConfig"]
    # SDK 3.6.1 gửi khóa `thinking_level` (snake_case); chấp nhận cả dạng camelCase nếu SDK đổi.
    assert thinking.get("thinking_level", thinking.get("thinkingLevel")) == "LOW"


def test_empty_thinking_level_uses_model_default():
    recorder = Recorder(ok())
    client = httpx2.Client(transport=httpx2.MockTransport(recorder))
    GeminiProvider(SecretStr(FAKE_KEY), thinking_level="", http_client=client).generate(REQUEST, model="m", timeout_seconds=5)
    assert "thinkingConfig" not in json.loads(recorder.requests[0].content)["generationConfig"]


@pytest.mark.parametrize(("raw", "expected"), [(" Medium ", "medium"), ("", ""), ("minimal", "minimal")])
def test_thinking_level_setting_is_normalized(raw, expected):
    assert GeminiSettings(_env_file=None, gemini_thinking_level=raw).gemini_thinking_level == expected


def test_invalid_thinking_level_is_rejected():
    with pytest.raises(ValueError, match="GEMINI_THINKING_LEVEL"):
        GeminiSettings(_env_file=None, gemini_thinking_level="turbo")


def test_max_tokens_with_text_is_returned_and_marked_truncated():
    response = make_provider(Recorder(ok("Câu trả lời dở dang", finish="MAX_TOKENS"))).generate(
        REQUEST, model="m", timeout_seconds=5
    )
    assert response.text == "Câu trả lời dở dang"
    assert response.truncated is True


@pytest.mark.parametrize("finish", ["STOP", "FINISH_REASON_UNSPECIFIED"])
def test_normal_finish_is_not_truncated(finish):
    response = make_provider(Recorder(ok(finish=finish))).generate(REQUEST, model="m", timeout_seconds=5)
    assert response.truncated is False


def test_missing_finish_reason_is_not_truncated():
    body = {"candidates": [{"content": {"role": "model", "parts": [{"text": "ok"}]}}]}
    assert make_provider(Recorder((200, body))).generate(REQUEST, model="m", timeout_seconds=5).truncated is False


def test_max_tokens_without_text_is_invalid_not_truncated():
    with pytest.raises(LLMInvalidResponseError):
        make_provider(Recorder(ok(parts=[], finish="MAX_TOKENS"))).generate(REQUEST, model="m", timeout_seconds=5)


def test_truncated_flag_passes_through_service_and_logs_without_content(caplog):
    secret_answer = "noi-dung-tra-loi-bi-cat-91x"
    caplog.set_level(logging.DEBUG)
    service = LLMService(make_provider(Recorder(ok(secret_answer, finish="MAX_TOKENS"))), model="m", max_retries=0)

    result = service.generate(REQUEST)

    assert result.truncated is True and result.text == secret_answer
    assert "truncated=True" in caplog.text and "truncated=True" in repr(result)
    for text in (caplog.text, repr(result)):
        assert secret_answer not in text


def test_thought_parts_are_excluded_from_text():
    parts = [{"text": "suy nghĩ nội bộ", "thought": True}, {"text": "Đáp án"}]
    response = make_provider(Recorder(ok(parts=parts))).generate(REQUEST, model="m", timeout_seconds=5)
    assert response.text == "Đáp án"


def test_missing_usage_and_model_version_are_tolerated():
    response = make_provider(Recorder(ok(usage=False, model_version=None))).generate(REQUEST, model="m", timeout_seconds=5)
    assert (response.input_tokens, response.output_tokens, response.model) == (None, None, "m")


# ---------- Structured output ----------


class Level(BaseModel):
    level_code: str


def test_structured_output_sends_schema_and_service_parses_it():
    recorder = Recorder(ok('{"level_code": "A2"}'))
    service = LLMService(make_provider(recorder), model="m", max_retries=0)

    result = service.generate(LLMRequest("s", REQUEST.messages, response_schema=Level))

    config = json.loads(recorder.requests[0].content)["generationConfig"]
    assert config["responseMimeType"] == "application/json"
    assert "level_code" in json.dumps(config["responseSchema"])
    assert result.parsed == Level(level_code="A2")


def test_truncated_structured_output_is_invalid():
    recorder = Recorder(ok('{"level_co', finish="MAX_TOKENS"))
    service = LLMService(make_provider(recorder), model="m", max_retries=2)

    with pytest.raises(LLMInvalidResponseError):
        service.generate(LLMRequest("s", REQUEST.messages, response_schema=Level))
    assert len(recorder.requests) == 1  # sai định dạng không thử lại


# ---------- Bị chặn / rỗng ----------


@pytest.mark.parametrize(
    "body",
    [
        {"promptFeedback": {"blockReason": "SAFETY"}},
        {"promptFeedback": {"blockReason": "JAILBREAK"}, "candidates": []},
        ok(finish="SAFETY")[1],
        ok(finish="PROHIBITED_CONTENT")[1],
        ok(finish="RECITATION")[1],
    ],
)
def test_safety_blocks_map_to_content_blocked(body):
    with pytest.raises(LLMContentBlockedError):
        make_provider(Recorder((200, body))).generate(REQUEST, model="m", timeout_seconds=5)


@pytest.mark.parametrize("body", [{"candidates": []}, ok(parts=[])[1], ok("   ")[1], {}])
def test_empty_responses_are_invalid(body):
    with pytest.raises(LLMInvalidResponseError):
        make_provider(Recorder((200, body))).generate(REQUEST, model="m", timeout_seconds=5)


# ---------- Ánh xạ lỗi HTTP ----------


@pytest.mark.parametrize(
    ("response", "expected", "retry_after"),
    [
        (error(429, "RESOURCE_EXHAUSTED", [QUOTA_PER_DAY, retry_info("30s")]), LLMQuotaExhaustedError, 30.0),
        (error(429, "RESOURCE_EXHAUSTED", [QUOTA_PER_MINUTE, retry_info("7.5s")]), LLMRateLimitError, 7.5),
        (error(429, "RESOURCE_EXHAUSTED"), LLMRateLimitError, None),
        (error(402, "PAYMENT_REQUIRED"), LLMQuotaExhaustedError, None),
        (error(400, "INVALID_ARGUMENT"), LLMConfigError, None),
        (error(403, "PERMISSION_DENIED"), LLMConfigError, None),
        (error(404, "NOT_FOUND"), LLMConfigError, None),
        (error(408, "DEADLINE_EXCEEDED"), LLMTimeoutError, None),
        (error(500, "INTERNAL"), LLMProviderError, None),
        (error(503, "UNAVAILABLE"), LLMProviderError, None),
        (error(504, "DEADLINE_EXCEEDED"), LLMTimeoutError, None),
    ],
)
def test_http_errors_map_to_standard_errors_without_sdk_retry(response, expected, retry_after):
    recorder = Recorder(response)

    with pytest.raises(expected) as caught:
        make_provider(recorder).generate(REQUEST, model="m", timeout_seconds=5)

    assert type(caught.value) is expected
    assert caught.value.retry_after == retry_after
    assert len(recorder.requests) == 1  # SDK không tự thử lại (LLMService mới quyết định)
    assert "chi tiết nội bộ" not in str(caught.value)  # không mang message của máy chủ ra ngoài


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (httpx2.ReadTimeout("hết giờ"), LLMTimeoutError),
        (httpx2.ConnectTimeout("hết giờ"), LLMTimeoutError),
        (httpx2.ConnectError("mất mạng"), LLMProviderError),
    ],
)
def test_transport_errors_map_to_standard_errors(exc, expected):
    recorder = Recorder(exc)
    with pytest.raises(expected):
        make_provider(recorder).generate(REQUEST, model="m", timeout_seconds=5)
    assert len(recorder.requests) == 1


def test_service_retries_transient_gemini_error_exactly_once():
    recorder = Recorder(error(503, "UNAVAILABLE"), ok("ok"))
    service = LLMService(make_provider(recorder), model="m", max_retries=1, sleep=lambda _: None)

    result = service.generate(REQUEST)

    assert result.text == "ok" and result.attempts == 2
    assert len(recorder.requests) == 2  # 1 + 1 thử lại của LLMService, không nhân với SDK


def test_daily_quota_falls_back_to_second_model():
    recorder = Recorder(error(429, "RESOURCE_EXHAUSTED", [QUOTA_PER_DAY]), ok("ok", model_version="model-phu-001"))
    service = LLMService(make_provider(recorder), model="model-chinh", fallback_models=("model-phu",), sleep=lambda _: None)

    result = service.generate(REQUEST)

    assert [r.url.path.rsplit("/", 1)[-1] for r in recorder.requests] == [
        "model-chinh:generateContent",
        "model-phu:generateContent",
    ]
    assert result.fallback_used and result.model == "model-phu-001"


# ---------- Cấu hình và key ----------


@pytest.mark.parametrize("key", [None, SecretStr(""), SecretStr("   ")])
def test_missing_key_is_config_error(key):
    with pytest.raises(LLMConfigError, match="GEMINI_API_KEY"):
        GeminiProvider(key)


def test_factory_reads_key_only_through_gemini_settings(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(gemini_module, "GeminiSettings", lambda: GeminiSettings(_env_file=None))
    with pytest.raises(LLMConfigError):
        build_llm_service(Settings(_env_file=None, llm_provider="gemini", llm_model_id="m"))

    monkeypatch.setattr(gemini_module, "GeminiSettings", lambda: GeminiSettings(_env_file=None, gemini_api_key=FAKE_KEY))
    service = build_llm_service(Settings(_env_file=None, llm_provider="gemini", llm_model_id="m", llm_max_output_tokens=300))
    assert isinstance(service.provider, GeminiProvider)
    assert service.default_max_output_tokens == 300


def test_gemini_provider_requires_model_id(monkeypatch):
    monkeypatch.setattr(gemini_module, "GeminiSettings", lambda: GeminiSettings(_env_file=None, gemini_api_key=FAKE_KEY))
    with pytest.raises(LLMConfigError, match="LLM_MODEL_ID"):
        build_llm_service(Settings(_env_file=None, llm_provider="gemini", llm_model_id=""))


def test_key_never_leaks_into_logs_reprs_errors_or_tracebacks(caplog):
    caplog.set_level(logging.DEBUG)  # gồm cả logger của httpx2/httpcore2/google_genai
    recorder = Recorder(ok(), error(403, "PERMISSION_DENIED"), error(429, "RESOURCE_EXHAUSTED"), httpx2.ReadTimeout("x"))
    provider = make_provider(recorder)
    service = LLMService(provider, model="m", max_retries=0)

    captured: list[str] = [repr(provider), repr(service), repr(service.generate(REQUEST))]
    for _ in range(3):
        try:
            service.generate(REQUEST)
        except LLMError as exc:
            captured += [str(exc), repr(exc), exc.detail, "".join(traceback.format_exception(exc))]

    assert len(recorder.requests) == 4
    for text in [caplog.text, *captured]:
        assert FAKE_KEY not in text
    assert FAKE_KEY not in repr(GeminiSettings(_env_file=None, gemini_api_key=FAKE_KEY))
