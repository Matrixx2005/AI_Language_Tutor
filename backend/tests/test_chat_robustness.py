"""Không giữ kết nối DB khi chờ LLM; lỗi ngoài dự kiến; list_messages lấy tin mới nhất."""
import logging

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session

from app.api.deps import get_llm
from app.core.config import get_settings
from app.llm.fake import FakeLLM
from app.llm.service import LLMService
from app.models import ChatMessageRow, ChatSession, LearnerProfile, User
from app.services import chat as chat_service

SESSIONS = "/api/v1/chat/sessions"


class ProbeLLM(FakeLLM):
    """FakeLLM gọi `probe()` NGAY TRONG lúc generate để quan sát trạng thái DB."""

    def __init__(self, probe):
        super().__init__()
        self.probe = probe
        self.observations: list = []

    def generate(self, request, *, model, timeout_seconds):
        self.observations.append(self.probe())
        return super().generate(request, model=model, timeout_seconds=timeout_seconds)


def use_llm(client, provider):
    service = LLMService(provider, model="fake-model", max_retries=0, sleep=lambda _: None)
    client.app.dependency_overrides[get_llm] = lambda: service
    return service


def new_session(client, headers) -> str:
    return client.post(SESSIONS, headers=headers).json()["session_id"]


# ---------- 1. Không có transaction mở khi chờ LLM ----------


def test_no_open_transaction_while_llm_runs(client, register_and_login, db_session):
    probe = ProbeLLM(lambda: db_session.in_transaction())
    use_llm(client, probe)
    headers = register_and_login()
    session_id = new_session(client, headers)

    response = client.post(f"{SESSIONS}/{session_id}/messages", headers=headers, json={"content": "hi"})

    assert response.status_code == 200
    assert probe.observations == [False]


def test_no_pooled_connection_is_held_while_llm_runs():
    """Session thật (không dùng savepoint của test): đếm kết nối đang mượn từ pool lúc LLM chạy."""
    engine = create_engine(get_settings().database_url(test=True), connect_args={"connect_timeout": 5})
    db = Session(bind=engine, expire_on_commit=False)
    probe = ProbeLLM(lambda: engine.pool.checkedout())
    llm = LLMService(probe, model="fake-model", max_retries=0)
    try:
        user = User(email="pool-probe@example.com", password_hash="x")
        user.profile = LearnerProfile(language_code="en", current_level_code="A1")
        db.add(user)
        db.commit()
        chat = chat_service.create_session(db, user)

        _, reply = chat_service.send_message(db, llm, user, chat.session_id, "hi")

        assert reply.status == "ok"
        assert probe.observations == [0]  # không kết nối nào bị giữ trong lúc chờ LLM
    finally:
        db.rollback()
        db.execute(delete(ChatMessageRow).where(ChatMessageRow.session_id.in_(
            select(ChatSession.session_id).join(User).where(User.email == "pool-probe@example.com"))))
        db.execute(delete(ChatSession).where(ChatSession.user_id.in_(
            select(User.user_id).where(User.email == "pool-probe@example.com"))))
        db.execute(delete(LearnerProfile).where(LearnerProfile.user_id.in_(
            select(User.user_id).where(User.email == "pool-probe@example.com"))))
        db.execute(delete(User).where(User.email == "pool-probe@example.com"))
        db.commit()
        db.close()
        engine.dispose()


# ---------- 2. Lỗi ngoài dự kiến ----------


class BrokenService:
    """Lớp LLM bị lỗi lập trình (không phải LLMError)."""

    def __init__(self):
        self.calls = 0

    def generate(self, request):
        self.calls += 1
        raise RuntimeError("chi-tiet-noi-bo-khong-duoc-lo")


def test_unexpected_error_saves_internal_error_turn_and_returns_500(client, register_and_login, caplog):
    broken = BrokenService()
    client.app.dependency_overrides[get_llm] = lambda: broken
    headers = register_and_login()
    session_id = new_session(client, headers)
    caplog.set_level(logging.DEBUG)
    raw = TestClient(client.app, raise_server_exceptions=False)  # nhận phản hồi 500 thay vì exception

    response = raw.post(f"{SESSIONS}/{session_id}/messages", headers=headers, json={"content": "cau-hoi-9931"})

    assert response.status_code == 500
    assert response.json() == {"error": {"code": "internal_error", "message": "Đã có lỗi ngoài dự kiến. Vui lòng thử lại sau."}}
    assert "chi-tiet-noi-bo" not in response.text and "Traceback" not in response.text
    history = client.get(f"{SESSIONS}/{session_id}/messages", headers=headers).json()
    assert [(m["role"], m["status"], m["error_code"]) for m in history] == [
        ("user", "ok", None),
        ("assistant", "error", "internal_error"),
    ]
    assert "chat internal_error session=" in caplog.text and "exc_type=RuntimeError" in caplog.text
    assert "cau-hoi-9931" not in caplog.text and "chi-tiet-noi-bo" not in caplog.text


def test_internal_error_turn_is_not_resent_to_llm(client, register_and_login):
    headers = register_and_login()
    session_id = new_session(client, headers)
    client.app.dependency_overrides[get_llm] = lambda: BrokenService()
    TestClient(client.app, raise_server_exceptions=False).post(
        f"{SESSIONS}/{session_id}/messages", headers=headers, json={"content": "câu bị lỗi"}
    )
    provider = FakeLLM()
    use_llm(client, provider)

    client.post(f"{SESSIONS}/{session_id}/messages", headers=headers, json={"content": "câu tiếp theo"})

    assert [(m.role, m.content) for m in provider.calls[-1].request.messages] == [("user", "câu tiếp theo")]


def test_provider_runtime_error_is_normalized_by_llm_service(client, register_and_login):
    class RaisingProvider(FakeLLM):
        def generate(self, request, *, model, timeout_seconds):
            raise RuntimeError("chi-tiet-noi-bo")

    use_llm(client, RaisingProvider())
    headers = register_and_login()
    session_id = new_session(client, headers)

    response = client.post(f"{SESSIONS}/{session_id}/messages", headers=headers, json={"content": "hi"})

    # LLMService chuẩn hóa lỗi lạ của provider (Buổi 1) → mã ổn định, không phải 500.
    assert response.status_code == 502 and response.json()["error"]["code"] == "llm_invalid_response"
    assert "chi-tiet-noi-bo" not in response.text


# ---------- 3. list_messages: tin mới nhất, thứ tự tăng dần ----------


def test_list_messages_returns_newest_in_chronological_order(client, register_and_login, db_session):
    provider = FakeLLM()
    use_llm(client, provider)
    headers = register_and_login()
    session_id = new_session(client, headers)
    for i in range(1, 5):
        provider.queue(f"trả lời {i}")
        client.post(f"{SESSIONS}/{session_id}/messages", headers=headers, json={"content": f"câu {i}"})
    user = db_session.scalar(select(User).where(User.email == "learner@example.com"))

    rows = chat_service.list_messages(db_session, user, session_id, limit=3)

    assert [r.content for r in rows] == ["trả lời 3", "câu 4", "trả lời 4"]  # 3 tin mới nhất, tăng dần
    times = [r.created_at for r in rows]
    assert times == sorted(times)
