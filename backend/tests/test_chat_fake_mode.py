"""LLM_PROVIDER=fake: không tính vào giới hạn ngày/toàn hệ thống, nhưng vẫn chống spam."""
import pytest
from sqlalchemy import select

from app.api.deps import get_llm
from app.llm.errors import LLMProviderError
from app.llm.fake import Fail, FakeLLM
from app.llm.service import LLMService
from app.models import ChatMessageRow, User

SESSIONS = "/api/v1/chat/sessions"


def use(client, provider: FakeLLM) -> FakeLLM:
    service = LLMService(provider, model="gemini-3.5-flash-lite", max_retries=0, sleep=lambda _: None)
    client.app.dependency_overrides[get_llm] = lambda: service
    return provider


def new_session(client, headers) -> str:
    return client.post(SESSIONS, headers=headers).json()["session_id"]


def send(client, headers, session_id, content="hi"):
    return client.post(f"{SESSIONS}/{session_id}/messages", headers=headers, json={"content": content})


def assistant_model_ids(db_session) -> list[str | None]:
    return list(db_session.scalars(
        select(ChatMessageRow.model_id).where(ChatMessageRow.role == "assistant").order_by(ChatMessageRow.created_at)
    ))


def test_fake_turns_are_marked_even_when_model_id_looks_real(client, register_and_login, db_session):
    provider = use(client, FakeLLM())  # như .env: LLM_PROVIDER=fake + LLM_MODEL_ID=gemini-...
    headers = register_and_login()
    session_id = new_session(client, headers)
    provider.queue("ok", Fail(LLMProviderError()))

    send(client, headers, session_id)
    send(client, headers, session_id)

    assert assistant_model_ids(db_session) == ["fake:gemini-3.5-flash-lite", "fake:"]


def test_real_turns_are_not_marked(client, register_and_login, db_session):
    use(client, FakeLLM(consumes_quota=True))
    headers = register_and_login()
    send(client, headers, new_session(client, headers))
    assert assistant_model_ids(db_session) == ["gemini-3.5-flash-lite"]


def test_fake_turns_do_not_use_daily_or_global_quota(client, register_and_login, limited):
    limited(chat_user_per_day=1, llm_global_per_day=1, llm_global_per_minute=1, chat_user_per_minute=0)
    use(client, FakeLLM())
    headers = register_and_login()
    session_id = new_session(client, headers)

    statuses = [send(client, headers, session_id, f"thử giao diện {i}").status_code for i in range(4)]

    assert statuses == [200, 200, 200, 200]


def test_fake_mode_ignores_provider_cooldown(client, register_and_login, limited):
    limited(chat_user_per_minute=0)
    client.app.state.limits.llm_cooldown.block(60)  # còn tạm khóa từ một lỗi 429 thật trước đó
    use(client, FakeLLM())
    headers = register_and_login()
    assert send(client, headers, new_session(client, headers)).status_code == 200


def test_fake_mode_still_limits_per_minute_and_concurrency(client, register_and_login, limited, db_session):
    limited(chat_user_per_minute=1)
    use(client, FakeLLM())
    headers = register_and_login()
    session_id = new_session(client, headers)
    assert send(client, headers, session_id).status_code == 200
    assert send(client, headers, session_id).json()["error"]["code"] == "chat_rate_limited"

    limited(chat_user_per_minute=0)
    user_id = db_session.scalar(select(User.user_id).where(User.email == "learner@example.com"))
    guard = client.app.state.limits.chat_in_flight
    guard.acquire(str(user_id), 1)
    assert send(client, headers, session_id).json()["error"]["code"] == "chat_busy"
    guard.release(str(user_id))


@pytest.mark.parametrize("fake_first", [2, 5])
def test_fake_turns_do_not_count_after_switching_to_real(client, register_and_login, limited, fake_first):
    limited(chat_user_per_day=1, llm_global_per_day=1, chat_user_per_minute=0)
    headers = register_and_login()
    session_id = new_session(client, headers)
    use(client, FakeLLM())
    for _ in range(fake_first):
        send(client, headers, session_id, "thử giao diện")

    use(client, FakeLLM(consumes_quota=True))  # chuyển sang gọi thật
    assert send(client, headers, session_id, "câu hỏi thật 1").status_code == 200
    limited_again = send(client, headers, session_id, "câu hỏi thật 2")
    assert limited_again.status_code == 429
    assert limited_again.json()["error"]["code"] in {"chat_daily_limit_reached", "service_busy"}
