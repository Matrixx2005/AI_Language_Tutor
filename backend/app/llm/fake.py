"""FakeLLM: nhà cung cấp giả, không mạng, lập trình được từng bước. Dùng cho test và cho
phát triển giao diện (LLM_PROVIDER=fake) mà không tốn hạn mức API thật.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass

from app.llm.errors import LLMError
from app.llm.provider import LLMProvider
from app.llm.types import LLMRequest, ProviderResponse

DEFAULT_REPLY = "Đây là câu trả lời thử nghiệm từ FakeLLM (chưa kết nối AI thật)."


@dataclass(frozen=True)
class Reply:
    text: str
    model: str | None = None  # None → dùng model được yêu cầu
    input_tokens: int | None = 10
    output_tokens: int | None = 20
    truncated: bool = False  # giả lập trả lời bị cắt vì chạm giới hạn token


@dataclass(frozen=True)
class Fail:
    error: LLMError


@dataclass(frozen=True)
class Delay:
    seconds: float
    then: Reply | Fail = Reply(DEFAULT_REPLY)


Step = Reply | Fail | Delay | str


@dataclass(frozen=True)
class FakeCall:
    model: str
    request: LLMRequest
    timeout_seconds: float


class FakeLLM(LLMProvider):
    name = "fake"
    default_model = "fake-model"

    def __init__(
        self, steps: Iterable[Step] = (), *, default: Step = DEFAULT_REPLY, consumes_quota: bool = False
    ) -> None:
        # Mặc định KHÔNG tốn hạn mức (đúng với LLM_PROVIDER=fake). Test cần giả lập nhà cung cấp
        # thật (giới hạn toàn hệ thống, tạm khóa sau 429) đặt consumes_quota=True.
        self.consumes_quota = consumes_quota
        self._steps: deque[Step] = deque(steps)
        self._default = default
        self._lock = threading.Lock()
        self.calls: list[FakeCall] = []

    def queue(self, *steps: Step) -> None:
        with self._lock:
            self._steps.extend(steps)

    def generate(self, request: LLMRequest, *, model: str, timeout_seconds: float) -> ProviderResponse:
        with self._lock:
            self.calls.append(FakeCall(model, request, timeout_seconds))
            step = self._steps.popleft() if self._steps else self._default
        return self._run(step, model)

    def _run(self, step: Step, model: str) -> ProviderResponse:
        if isinstance(step, str):
            step = Reply(step)
        if isinstance(step, Delay):
            time.sleep(step.seconds)
            return self._run(step.then, model)
        if isinstance(step, Fail):
            raise step.error
        return ProviderResponse(
            text=step.text,
            model=step.model or model,
            input_tokens=step.input_tokens,
            output_tokens=step.output_tokens,
            truncated=step.truncated,
        )
