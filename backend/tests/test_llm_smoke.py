"""Smoke test GỌI API THẬT — mặc định BỎ QUA.

Gửi dữ liệu ra ngoài và tốn hạn mức, nên chỉ chạy khi bật tường minh. Mỗi lần chạy đúng MỘT lời gọi:

    $env:RUN_LLM_SMOKE = "1"
    $env:LLM_PROVIDER = "gemini"; $env:LLM_MODEL_ID = "<model ID>"
    $env:LLM_SMOKE_CASE = "text"        # hoặc "structured", "bad_model"
    pytest backend/tests/test_llm_smoke.py -s

Chỉ in metadata (model, độ trễ, token, mã lỗi) — không in key.
"""
import os

import pytest
from pydantic import BaseModel

from app.core.config import Settings
from app.llm import build_llm_service
from app.llm.errors import LLMConfigError
from app.llm.types import ChatMessage, LLMRequest

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LLM_SMOKE") != "1", reason="smoke test gọi API thật; đặt RUN_LLM_SMOKE=1 để chạy"
)


class ArticleAnswer(BaseModel):
    article: str
    reason_vi: str


def test_real_llm_smoke():
    case = os.environ.get("LLM_SMOKE_CASE", "text")
    # Không thử lại, không model dự phòng: đúng một lời gọi, tiết kiệm hạn mức.
    # 512: token "suy nghĩ" của Gemini cũng tính vào giới hạn này (docs/thinking).
    settings = Settings(llm_max_retries=0, llm_fallback_model_ids="", llm_max_output_tokens=512)
    service = build_llm_service(settings)

    if case == "bad_model":
        bad = Settings(llm_max_retries=0, llm_fallback_model_ids="", llm_model_id="khong-ton-tai-model-xyz")
        with pytest.raises(LLMConfigError) as caught:
            build_llm_service(bad).generate(
                LLMRequest("Trả lời ngắn.", (ChatMessage("user", "Hi"),), max_output_tokens=16)
            )
        print(f"\n[smoke bad_model] code={caught.value.code} detail={caught.value.detail}")
        return

    if case == "structured":
        request = LLMRequest(
            system_prompt="Bạn là gia sư tiếng Anh cho người Việt. Trả lời đúng schema JSON.",
            messages=(ChatMessage("user", "Điền a hay an trước 'apple'? Giải thích ngắn bằng tiếng Việt."),),
            response_schema=ArticleAnswer,
        )
    else:
        request = LLMRequest(
            system_prompt="Bạn là gia sư tiếng Anh cho người Việt. Trả lời ngắn gọn bằng tiếng Việt.",
            messages=(ChatMessage("user", "Khi nào dùng 'a' và khi nào dùng 'an'? Trả lời trong 2 câu."),),
        )

    result = service.generate(request)

    print(
        f"\n[smoke {case}] requested={result.requested_model} model={result.model} "
        f"latency_ms={result.latency_ms} input_tokens={result.input_tokens} "
        f"output_tokens={result.output_tokens} attempts={result.attempts}"
    )
    print(f"[smoke {case}] text={result.text[:300]!r}")
    assert result.text.strip()
    assert result.attempts == 1
    if case == "structured":
        assert isinstance(result.parsed, ArticleAnswer)
        print(f"[smoke structured] parsed={result.parsed!r}")
