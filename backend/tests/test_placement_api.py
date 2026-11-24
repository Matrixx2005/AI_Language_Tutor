"""Placement API + nạp ngân hàng câu hỏi (DB test, rollback; bộ câu hỏi THẬT placement_v1.json)."""
import hashlib
import json
import threading
import time
import uuid

import pytest
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.models import LearnerProfile, PlacementResult, Question, User
from app.services import placement as placement_service
from app.services.question_bank import DEFAULT_PLACEMENT_FILE, QuestionBankError, load_questions, read_placement_file

ATTEMPTS = "/api/v1/placement/attempts"
FORBIDDEN_KEYS = {"correct_answer", "explanation", "is_correct", "level_code", "topic", "answer_summary"}


@pytest.fixture
def bank(db_session) -> list[Question]:
    load_questions(db_session, read_placement_file(), "placement_v1")
    return list(db_session.scalars(select(Question).order_by(Question.external_id)))


def keys_deep(value) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in keys_deep(v)}
    if isinstance(value, list):
        return {k for v in value for k in keys_deep(v)}
    return set()


def start(client, headers):
    return client.post(ATTEMPTS, headers=headers)


def answer_key(db_session, attempt_json, n_correct: int) -> dict[str, str]:
    """Đúng n câu đầu (theo thứ tự đề), sai các câu sau. Đáp án đọc từ DB, không từ API."""
    ids = [q["question_id"] for q in attempt_json["questions"]]
    rows = {str(q.question_id): q for q in db_session.scalars(select(Question))}
    answers = {}
    for i, qid in enumerate(ids):
        q = rows[qid]
        answers[qid] = q.correct_answer if i < n_correct else next(o for o in q.options if o != q.correct_answer)
    return answers


def submit(client, headers, attempt_id, answers):
    return client.post(f"{ATTEMPTS}/{attempt_id}/submit", headers=headers, json={"answers": answers})


# ---------- Nạp ngân hàng câu hỏi ----------


def test_loader_is_idempotent_and_does_not_modify_source(db_session):
    before = hashlib.sha256(DEFAULT_PLACEMENT_FILE.read_bytes()).hexdigest()
    records = read_placement_file()

    first = load_questions(db_session, records, "placement_v1")
    second = load_questions(db_session, records, "placement_v1")

    assert (first.inserted, first.updated, first.unchanged) == (30, 0, 0)
    assert (second.inserted, second.updated, second.unchanged) == (0, 0, 30)
    assert db_session.scalar(select(Question).where(Question.external_id == "place-en-b1-grammar-021")).correct_answer == "since"
    assert hashlib.sha256(DEFAULT_PLACEMENT_FILE.read_bytes()).hexdigest() == before


def test_loader_updates_changed_question(db_session):
    records = read_placement_file()
    load_questions(db_session, records, "placement_v1")
    records[0] = {**records[0], "explanation": "Giải thích mới."}
    assert load_questions(db_session, records, "placement_v1").updated == 1


def test_loader_rejects_invalid_file_and_writes_nothing(db_session, tmp_path):
    bad = read_placement_file()
    bad[0] = {**bad[0], "correct_answer": "khong-co-trong-lua-chon"}
    path = tmp_path / "placement_bad.json"
    path.write_text(json.dumps(bad), encoding="utf-8")

    with pytest.raises(QuestionBankError) as caught:
        read_placement_file(path)

    assert any("correct_answer" in e for e in caught.value.errors)
    assert db_session.scalars(select(Question)).all() == []


# ---------- Bắt đầu bài: không lộ đáp án ----------


def test_start_returns_questions_without_answers(client, register_and_login, bank):
    headers = register_and_login()

    response = start(client, headers)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "in_progress" and body["result"] is None
    assert len(body["questions"]) == 30
    assert not keys_deep(body) & FORBIDDEN_KEYS
    assert all(set(q) == {"question_id", "position", "category", "prompt", "options"} for q in body["questions"])
    # GET khi đang làm cũng không lộ
    again = client.get(f"{ATTEMPTS}/{body['attempt_id']}", headers=headers).json()
    assert not keys_deep(again) & FORBIDDEN_KEYS


def test_second_start_resumes_same_attempt(client, register_and_login, bank):
    headers = register_and_login()
    first = start(client, headers).json()
    second = start(client, headers)
    assert second.status_code == 200 and second.json()["attempt_id"] == first["attempt_id"]


def test_openapi_schema_never_exposes_answers_for_questions():
    from app.main import create_app

    schema = create_app().openapi()["components"]["schemas"]["PlacementQuestionRead"]["properties"]
    assert not set(schema) & FORBIDDEN_KEYS


# ---------- Nộp bài: điểm và ngưỡng (tính tay: 30 câu, A2 ≥ 12, B1 ≥ 21) ----------


@pytest.mark.parametrize(("n_correct", "level"), [(30, "B1"), (21, "B1"), (20, "A2"), (12, "A2"), (11, "A1"), (0, "A1")])
def test_scores_and_levels_at_boundaries(client, register_and_login, bank, db_session, n_correct, level):
    headers = register_and_login()
    attempt = start(client, headers).json()

    result = submit(client, headers, attempt["attempt_id"], answer_key(db_session, attempt, n_correct)).json()["result"]

    assert (result["score"], result["max_score"], result["suggested_level_code"]) == (n_correct, 30, level)
    assert result["applied_at"] is None  # chỉ ĐỀ XUẤT, chưa đổi hồ sơ
    assert "không phải chứng chỉ CEFR" in result["disclaimer"] and "tạm thời" in result["disclaimer"]


def test_blank_submission(client, register_and_login, bank):
    headers = register_and_login()
    attempt = start(client, headers).json()

    result = submit(client, headers, attempt["attempt_id"], {}).json()["result"]

    assert (result["score"], result["suggested_level_code"]) == (0, "A1")
    assert len(result["weak_groups"]) == 6 and all(item["selected"] is None for item in result["review"])


def test_weak_groups_and_review_after_submit(client, register_and_login, bank, db_session):
    headers = register_and_login()
    attempt = start(client, headers).json()
    answers = answer_key(db_session, attempt, 30)
    a2_grammar = [q for q in bank if q.level_code == "A2" and q.category == "grammar"][:3]
    for q in a2_grammar:  # sai 3/5 câu ngữ pháp A2 → 40% < 60% → nhóm yếu
        answers[str(q.question_id)] = next(o for o in q.options if o != q.correct_answer)

    result = submit(client, headers, attempt["attempt_id"], answers).json()["result"]

    assert result["score"] == 27 and result["suggested_level_code"] == "B1"
    assert [(g["level_code"], g["category"], g["correct"], g["total"]) for g in result["weak_groups"]] == [("A2", "grammar", 2, 5)]
    assert set(result["missed_topics"]) == {q.topic for q in a2_grammar}
    review = {item["question_id"]: item for item in result["review"]}
    for q in a2_grammar:  # sau khi nộp mới được xem đáp án và giải thích
        item = review[str(q.question_id)]
        assert item["correct_answer"] == q.correct_answer and not item["is_correct"] and item["explanation"]


# ---------- Nộp trùng / câu lạ / lựa chọn lạ ----------


def test_cannot_submit_twice(client, register_and_login, bank, db_session):
    headers = register_and_login()
    attempt = start(client, headers).json()
    submit(client, headers, attempt["attempt_id"], answer_key(db_session, attempt, 30))

    again = submit(client, headers, attempt["attempt_id"], {})

    assert again.status_code == 409 and again.json()["error"]["code"] == "placement_already_submitted"
    assert client.get(f"{ATTEMPTS}/{attempt['attempt_id']}", headers=headers).json()["result"]["score"] == 30


def test_unknown_question_and_invalid_option_are_rejected_without_closing_attempt(client, register_and_login, bank, db_session):
    headers = register_and_login()
    attempt = start(client, headers).json()
    first_id = attempt["questions"][0]["question_id"]

    unknown = submit(client, headers, attempt["attempt_id"], {str(uuid.uuid4()): "is"})
    invalid = submit(client, headers, attempt["attempt_id"], {first_id: "khong-co-trong-de"})

    assert unknown.status_code == 422 and unknown.json()["error"]["code"] == "unknown_question"
    assert invalid.status_code == 422 and invalid.json()["error"]["code"] == "invalid_option"
    assert submit(client, headers, attempt["attempt_id"], {}).status_code == 200  # lượt vẫn mở


def test_concurrent_double_submit_only_one_succeeds(monkeypatch):
    """Hai luồng THẬT nộp cùng lúc; chấm điểm bị làm chậm để mở rộng khe hở race."""
    settings = get_settings()
    # lock_timeout: FOR UPDATE không bao giờ chờ vô hạn → test không thể treo tiến trình pytest.
    engine = create_engine(settings.database_url(test=True), connect_args={"connect_timeout": 5, "options": "-c lock_timeout=15000"})
    email = "placement-race@example.com"
    setup = Session(bind=engine)
    load_questions(setup, read_placement_file(), "placement_v1")
    user = User(email=email, password_hash="x")
    user.profile = LearnerProfile(language_code="en", current_level_code="A1")
    setup.add(user)
    setup.commit()
    attempt, _, _ = placement_service.start_attempt(setup, user)
    attempt_id = attempt.result_id
    setup.close()

    original = placement_service.score_placement

    def slow_score(*args, **kwargs):
        time.sleep(0.3)
        return original(*args, **kwargs)

    monkeypatch.setattr(placement_service, "score_placement", slow_score)
    results: list[str] = []
    barrier = threading.Barrier(2)

    def worker():
        db = Session(bind=engine)
        try:
            me = db.scalar(select(User).where(User.email == email))
            barrier.wait(timeout=15)
            placement_service.submit_attempt(db, me, attempt_id, {})
            results.append("ok")
        except AppError as error:
            results.append(error.code)
        except Exception as exc:  # lỗi bất ngờ (kể cả hết lock_timeout) vẫn được ghi nhận
            results.append(type(exc).__name__)
        finally:
            db.close()

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(2)]
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)
        assert sorted(results) == ["ok", "placement_already_submitted"]
    finally:
        cleanup = Session(bind=engine)
        user_ids = select(User.user_id).where(User.email == email)
        cleanup.execute(delete(PlacementResult).where(PlacementResult.user_id.in_(user_ids)))
        cleanup.execute(delete(LearnerProfile).where(LearnerProfile.user_id.in_(user_ids)))
        cleanup.execute(delete(User).where(User.email == email))
        cleanup.execute(delete(Question).where(Question.question_set == "placement_v1"))
        cleanup.commit()
        cleanup.close()
        engine.dispose()


# ---------- Quyền truy cập ----------


def test_other_user_cannot_view_submit_or_apply(client, register_and_login, bank):
    headers_a = register_and_login("a@example.com")
    headers_b = register_and_login("b@example.com")
    attempt_id = start(client, headers_a).json()["attempt_id"]

    responses = [
        client.get(f"{ATTEMPTS}/{attempt_id}", headers=headers_b),
        submit(client, headers_b, attempt_id, {}),
        client.post(f"{ATTEMPTS}/{attempt_id}/apply", headers=headers_b),
        client.get(f"{ATTEMPTS}/{uuid.uuid4()}", headers=headers_a),  # ID đoán mò
    ]

    assert all(r.status_code == 404 and r.json()["error"]["code"] == "placement_not_found" for r in responses)
    assert client.get(ATTEMPTS, headers=headers_b).json() == []
    assert client.get(f"{ATTEMPTS}/{attempt_id}", headers=headers_a).json()["status"] == "in_progress"


@pytest.mark.parametrize(("method", "path"), [("post", ATTEMPTS), ("get", ATTEMPTS), ("get", f"{ATTEMPTS}/{uuid.uuid4()}")])
def test_placement_requires_token(client, method, path):
    assert client.request(method.upper(), path).status_code == 401


# ---------- Ngôn ngữ không hỗ trợ / chưa nạp câu hỏi ----------


def test_unsupported_language_is_rejected(client, register_and_login, bank, db_session):
    headers = register_and_login()
    profile = db_session.scalar(select(LearnerProfile))
    profile.language_code = "ja"  # chưa có languages/ja.yaml
    db_session.flush()

    response = start(client, headers)

    assert response.status_code == 422 and response.json()["error"]["code"] == "placement_not_available"


def test_missing_question_bank_is_rejected(client, register_and_login):
    headers = register_and_login()  # không dùng fixture `bank`
    response = start(client, headers)
    assert response.status_code == 422 and response.json()["error"]["code"] == "placement_not_available"


# ---------- Xác nhận trình độ đề xuất ----------


def test_apply_requires_completed_attempt(client, register_and_login, bank):
    headers = register_and_login()
    attempt_id = start(client, headers).json()["attempt_id"]
    response = client.post(f"{ATTEMPTS}/{attempt_id}/apply", headers=headers)
    assert response.status_code == 409 and response.json()["error"]["code"] == "placement_not_completed"


def test_apply_updates_profile_only_when_confirmed(client, register_and_login, bank, db_session):
    headers = register_and_login()
    attempt = start(client, headers).json()
    submit(client, headers, attempt["attempt_id"], answer_key(db_session, attempt, 15))  # 50% → A2
    assert client.get("/api/v1/profile/me", headers=headers).json()["current_level_code"] == "A1"  # chưa đổi

    applied = client.post(f"{ATTEMPTS}/{attempt['attempt_id']}/apply", headers=headers)

    assert applied.status_code == 200 and applied.json()["current_level_code"] == "A2"
    detail = client.get(f"{ATTEMPTS}/{attempt['attempt_id']}", headers=headers).json()
    assert detail["result"]["applied_at"] is not None
    assert client.post(f"{ATTEMPTS}/{attempt['attempt_id']}/apply", headers=headers).status_code == 200  # gọi lại vẫn ổn


def test_retake_after_completion_creates_new_attempt(client, register_and_login, bank):
    headers = register_and_login()
    first = start(client, headers).json()
    submit(client, headers, first["attempt_id"], {})

    second = start(client, headers)

    assert second.status_code == 201 and second.json()["attempt_id"] != first["attempt_id"]
    assert [a["status"] for a in client.get(ATTEMPTS, headers=headers).json()] == ["in_progress", "completed"]
