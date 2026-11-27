"""Kiểm thử đầu-cuối Tuần 3 qua HTTP (Buổi 7).

Mỗi test đi trọn một luồng người dùng qua API thật của app (TestClient → router → service → PostgreSQL
DB test), giống những gì giao diện gọi. Không mạng, không key: LLM là FakeLLM lập trình được. Mỗi test
có app riêng (bộ đếm giới hạn riêng) và transaction riêng được rollback → không phụ thuộc thứ tự,
không để lại dữ liệu. Bộ câu hỏi placement là bộ THẬT `data/evaluation/placement_v1.json`.
"""
import logging
import uuid

import pytest
from sqlalchemy import select

from app.api.deps import get_llm
from app.llm.errors import LLMContentBlockedError, LLMRateLimitError, LLMTimeoutError
from app.llm.fake import Fail, FakeLLM, Reply
from app.llm.service import LLMService
from app.models import ChatMessageRow, Question
from app.services.question_bank import load_questions, read_placement_file

API = "/api/v1"
SESSIONS = f"{API}/chat/sessions"
ATTEMPTS = f"{API}/placement/attempts"
# Khóa không được xuất hiện ở bất kỳ đâu trong câu hỏi khi CHƯA nộp bài.
ANSWER_KEYS = {"correct_answer", "explanation", "is_correct", "level_code", "topic", "answer_summary", "result"}


@pytest.fixture
def fake_llm(client) -> FakeLLM:
    provider = FakeLLM()
    client.app.dependency_overrides[get_llm] = lambda: LLMService(
        provider, model="fake-model", max_retries=0, sleep=lambda _: None
    )
    return provider


@pytest.fixture
def placement_bank(db_session) -> dict[str, Question]:
    load_questions(db_session, read_placement_file(), "placement_v1")
    return {str(q.question_id): q for q in db_session.scalars(select(Question))}


def register(client, email: str, password: str = "mat-khau-an-toan") -> None:
    response = client.post(f"{API}/auth/register", json={"email": email, "password": password})
    assert response.status_code == 201, response.text


def login(client, email: str, password: str = "mat-khau-an-toan"):
    return client.post(f"{API}/auth/login", json={"email": email, "password": password})


def user(client, email: str) -> dict[str, str]:
    """Đăng ký + đăng nhập qua API như giao diện, trả header Authorization."""
    register(client, email)
    response = login(client, email)
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def new_session(client, headers) -> str:
    response = client.post(SESSIONS, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["session_id"]


def send(client, headers, session_id, content: str):
    return client.post(f"{SESSIONS}/{session_id}/messages", headers=headers, json={"content": content})


def history(client, headers, session_id):
    return client.get(f"{SESSIONS}/{session_id}/messages", headers=headers)


def keys_deep(value) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in keys_deep(v)}
    if isinstance(value, list):
        return {k for v in value for k in keys_deep(v)}
    return set()


def answers_with(bank: dict[str, Question], questions: list[dict], n_correct: int) -> dict[str, str]:
    """Đúng `n_correct` câu đầu, sai các câu còn lại. Đáp án đọc từ DB test, KHÔNG từ API."""
    answers = {}
    for i, q in enumerate(questions):
        row = bank[q["question_id"]]
        answers[q["question_id"]] = (
            row.correct_answer if i < n_correct else next(o for o in row.options if o != row.correct_answer)
        )
    return answers


# ---------- 1. Chat: đăng ký → đăng nhập → phiên → gửi → lịch sử ----------


def test_chat_flow_register_login_send_and_read_history_in_order(client, fake_llm, caplog):
    headers = user(client, "e2e-chat@example.com")
    me = client.get(f"{API}/profile/me", headers=headers).json()
    session_id = new_session(client, headers)
    fake_llm.queue("Trả lời 1", "Trả lời 2")

    with caplog.at_level(logging.DEBUG):
        first = send(client, headers, session_id, "Câu hỏi riêng tư số một")
        second = send(client, headers, session_id, "Câu hỏi riêng tư số hai")

    assert first.status_code == second.status_code == 200
    assert first.json()["assistant_message"]["content"] == "Trả lời 1"
    turns = history(client, headers, session_id).json()
    assert [(m["role"], m["content"], m["status"]) for m in turns] == [
        ("user", "Câu hỏi riêng tư số một", "ok"),
        ("assistant", "Trả lời 1", "ok"),
        ("user", "Câu hỏi riêng tư số hai", "ok"),
        ("assistant", "Trả lời 2", "ok"),
    ]
    sessions = client.get(SESSIONS, headers=headers).json()
    assert [s["session_id"] for s in sessions] == [session_id]
    assert sessions[0]["title"] == "Câu hỏi riêng tư số một"
    # Prompt hệ thống theo ngôn ngữ và trình độ của hồ sơ; lượt sau mang theo lịch sử.
    assert (me["language_code"], me["current_level_code"]) == ("en", "A1")
    request = fake_llm.calls[-1].request
    assert "A1" in request.system_prompt
    assert [m.content for m in request.messages] == [
        "Câu hỏi riêng tư số một", "Trả lời 1", "Câu hỏi riêng tư số hai",
    ]
    # Không lộ thông tin nội bộ cho client; log không chứa nội dung tin nhắn.
    assert "model_id" not in first.text and "input_tokens" not in first.text
    assert "riêng tư" not in caplog.text and "Trả lời 1" not in caplog.text


# ---------- 2. Người dùng B không đọc/ghi được phiên của A ----------


def test_other_user_cannot_read_or_write_session(client, fake_llm, db_session):
    alice = user(client, "e2e-alice@example.com")
    bob = user(client, "e2e-bob@example.com")
    session_id = new_session(client, alice)
    assert send(client, alice, session_id, "Tin của Alice").status_code == 200
    rows_before = len(db_session.scalars(select(ChatMessageRow)).all())

    read = history(client, bob, session_id)
    write = send(client, bob, session_id, "Bob chen vào")
    missing = history(client, bob, str(uuid.uuid4()))

    for response in (read, write, missing):
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "chat_session_not_found"
    assert "Tin của Alice" not in read.text
    # Câu trả lời giống hệt "không tồn tại" → không dò được phiên của người khác.
    assert read.json() == missing.json()
    assert client.get(SESSIONS, headers=bob).json() == []
    assert len(db_session.scalars(select(ChatMessageRow)).all()) == rows_before
    assert [m["content"] for m in history(client, alice, session_id).json()][0] == "Tin của Alice"


# ---------- 3. Giới hạn tần suất ----------


def test_chat_minute_limit_returns_429_with_retry_after(client, fake_llm, limited):
    limited(chat_user_per_minute=6)
    headers = user(client, "e2e-limit@example.com")
    session_id = new_session(client, headers)

    statuses = [send(client, headers, session_id, f"tin {i}").status_code for i in range(6)]
    blocked = send(client, headers, session_id, "tin thứ bảy")

    assert statuses == [200] * 6
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "chat_rate_limited"
    assert 1 <= int(blocked.headers["retry-after"]) <= 60
    # Tin bị chặn không được lưu, không gọi LLM.
    assert len(history(client, headers, session_id).json()) == 12
    assert len(fake_llm.calls) == 6


def test_login_lockout_after_repeated_failures(client, limited):
    limited(auth_login_fails_per_email=5, auth_login_window_seconds=900)
    register(client, "e2e-lock@example.com")

    wrong = [login(client, "e2e-lock@example.com", "sai-mat-khau-1").status_code for _ in range(5)]
    blocked = login(client, "e2e-lock@example.com", "mat-khau-an-toan")  # đúng mật khẩu vẫn bị chặn

    assert wrong == [401] * 5
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "auth_rate_limited"
    assert 1 <= int(blocked.headers["retry-after"]) <= 900
    assert "access_token" not in blocked.text


# ---------- 4. Placement: start → get → submit → kết quả → apply → hồ sơ ----------


def test_placement_flow_scores_applies_level_and_guards_resubmit_and_superseded(client, placement_bank):
    headers = user(client, "e2e-placement@example.com")

    started = client.post(ATTEMPTS, headers=headers)
    assert started.status_code == 201
    attempt = started.json()
    fetched = client.get(f"{ATTEMPTS}/{attempt['attempt_id']}", headers=headers)
    assert fetched.status_code == 200
    for body in (attempt, fetched.json()):
        assert body["status"] == "in_progress" and len(body["questions"]) == 30
        assert not (keys_deep(body["questions"]) & ANSWER_KEYS)
        assert body["result"] is None
    # Không đáp án nào lọt vào văn bản trả về dưới dạng giá trị của trường riêng.
    assert "correct_answer" not in started.text and "explanation" not in fetched.text

    # 12/30 = 40% → đúng ngưỡng A2 trong languages/en.yaml (so sánh nguyên, không làm tròn).
    answers = answers_with(placement_bank, attempt["questions"], n_correct=12)
    submitted = client.post(f"{ATTEMPTS}/{attempt['attempt_id']}/submit", headers=headers, json={"answers": answers})
    assert submitted.status_code == 200, submitted.text
    result = submitted.json()["result"]
    assert (result["score"], result["max_score"], result["suggested_level_code"]) == (12, 30, "A2")
    assert len(result["review"]) == 30 and result["disclaimer"]
    assert result["weak_groups"] and result["missed_topics"]
    assert all(r["correct_answer"] == placement_bank[r["question_id"]].correct_answer for r in result["review"])

    again = client.post(f"{ATTEMPTS}/{attempt['attempt_id']}/submit", headers=headers, json={"answers": answers})
    assert again.status_code == 409 and again.json()["error"]["code"] == "placement_already_submitted"

    # Lượt thứ hai (mới hơn) làm lượt đầu thành "cũ".
    second = client.post(ATTEMPTS, headers=headers).json()
    all_right = answers_with(placement_bank, second["questions"], n_correct=30)
    assert client.post(f"{ATTEMPTS}/{second['attempt_id']}/submit", headers=headers, json={"answers": all_right}).json()[
        "result"
    ]["suggested_level_code"] == "B1"

    stale = client.post(f"{ATTEMPTS}/{attempt['attempt_id']}/apply", headers=headers)
    assert stale.status_code == 409 and stale.json()["error"]["code"] == "placement_superseded"
    assert client.get(f"{API}/profile/me", headers=headers).json()["current_level_code"] == "A1"

    applied = client.post(f"{ATTEMPTS}/{second['attempt_id']}/apply", headers=headers)
    assert applied.status_code == 200 and applied.json()["current_level_code"] == "B1"
    assert client.get(f"{API}/profile/me", headers=headers).json()["current_level_code"] == "B1"
    # Phiên chat mới dùng trình độ vừa áp dụng.
    assert client.post(SESSIONS, headers=headers).json()["level_code"] == "B1"


def test_other_user_cannot_see_or_submit_placement_attempt(client, placement_bank):
    alice = user(client, "e2e-pa@example.com")
    bob = user(client, "e2e-pb@example.com")
    attempt = client.post(ATTEMPTS, headers=alice).json()

    seen = client.get(f"{ATTEMPTS}/{attempt['attempt_id']}", headers=bob)
    submitted = client.post(f"{ATTEMPTS}/{attempt['attempt_id']}/submit", headers=bob, json={"answers": {}})

    assert seen.status_code == submitted.status_code == 404
    assert seen.json()["error"]["code"] == "placement_not_found"
    assert client.get(ATTEMPTS, headers=bob).json() == []


# ---------- 5. Lỗi LLM: mã ổn định, không lộ nội bộ, lượt lỗi lưu status='error' ----------


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (LLMTimeoutError("upstream deadline 30s at gemini-internal-host"), 504, "llm_timeout"),
        (LLMRateLimitError("RESOURCE_EXHAUSTED project=secret-project", retry_after=17.2), 429, "llm_rate_limited"),
        (LLMContentBlockedError("SAFETY: HARM_CATEGORY_X blocked"), 422, "llm_content_blocked"),
    ],
)
def test_llm_failure_gives_stable_code_hides_internals_and_stores_error_turn(
    client, fake_llm, db_session, error, status, code
):
    headers = user(client, f"e2e-{code}@example.com")
    session_id = new_session(client, headers)
    fake_llm.queue(Fail(error))

    response = send(client, headers, session_id, "Câu hỏi khi AI lỗi")

    assert response.status_code == status
    body = response.json()
    assert set(body) == {"error"} and body["error"]["code"] == code
    for internal in (str(error), "gemini", "secret-project", "HARM_CATEGORY", "Traceback", "fake-model"):
        assert internal not in response.text
    if code == "llm_rate_limited":
        assert response.headers["retry-after"] == "17"
    turns = history(client, headers, session_id).json()
    assert [(m["role"], m["status"], m["error_code"]) for m in turns] == [
        ("user", "ok", None),
        ("assistant", "error", code),
    ]
    stored = db_session.scalars(select(ChatMessageRow).where(ChatMessageRow.role == "assistant")).one()
    assert (stored.status, stored.error_code) == ("error", code)

    # Không treo: lượt sau hoạt động bình thường và không gửi lại lượt lỗi cho LLM.
    fake_llm.queue(Reply("Đã ổn"))
    recovered = send(client, headers, session_id, "Hỏi lại")
    assert recovered.status_code == 200
    assert [m.content for m in fake_llm.calls[-1].request.messages] == ["Hỏi lại"]
