"""Lượt đang làm lỗi thời khi bộ câu hỏi đổi; apply chỉ với lượt hoàn thành mới nhất."""
import logging

import pytest
from sqlalchemy import select

from app.models import PlacementResult, Question
from app.services.question_bank import load_questions, read_placement_file

ATTEMPTS = "/api/v1/placement/attempts"


@pytest.fixture
def bank(db_session):
    load_questions(db_session, read_placement_file(), "placement_v1")


def start(client, headers):
    return client.post(ATTEMPTS, headers=headers)


def submit(client, headers, attempt_id, answers=None):
    return client.post(f"{ATTEMPTS}/{attempt_id}/submit", headers=headers, json={"answers": answers or {}})


def statuses(db_session) -> dict[str, str]:
    return {str(r.result_id): r.status for r in db_session.scalars(select(PlacementResult))}


def delete_one_question(db_session) -> None:
    db_session.delete(db_session.scalar(select(Question).order_by(Question.external_id).limit(1)))
    db_session.flush()


# ---------- 1. Lượt đang làm không còn khớp bộ câu hỏi ----------


def test_stale_in_progress_attempt_is_replaced_on_start(client, register_and_login, bank, db_session, caplog):
    headers_a = register_and_login("a@example.com")
    headers_b = register_and_login("b@example.com")
    done_a = start(client, headers_a).json()["attempt_id"]
    submit(client, headers_a, done_a)  # lượt ĐÃ NỘP trước đó của A
    done_b = start(client, headers_b).json()["attempt_id"]
    submit(client, headers_b, done_b)  # lượt đã nộp của người khác
    stale = start(client, headers_a).json()["attempt_id"]  # lượt đang làm của A
    delete_one_question(db_session)  # bộ câu hỏi đổi: còn 29 câu
    caplog.set_level(logging.INFO, logger="app.placement")

    # Xem lượt dở lỗi thời → 409, người dùng gọi start để làm mới
    detail = client.get(f"{ATTEMPTS}/{stale}", headers=headers_a)
    assert detail.status_code == 409 and detail.json()["error"]["code"] == "placement_questions_changed"

    fresh = start(client, headers_a)

    assert fresh.status_code == 201
    body = fresh.json()
    assert body["attempt_id"] != stale and len(body["questions"]) == 29  # đủ câu của bộ HIỆN TẠI
    remaining = statuses(db_session)
    assert stale not in remaining  # lượt dở cũ đã bị xóa
    assert remaining[done_a] == "completed" and remaining[done_b] == "completed"  # không đụng lượt đã nộp
    assert remaining[body["attempt_id"]] == "in_progress"
    assert f"stale_attempt_discarded attempt={stale}" in caplog.text


def test_valid_in_progress_attempt_is_still_resumed(client, register_and_login, bank):
    headers = register_and_login()
    first = start(client, headers).json()["attempt_id"]
    again = start(client, headers)
    assert again.status_code == 200 and again.json()["attempt_id"] == first


def test_completed_attempt_is_never_deleted_by_stale_cleanup(client, register_and_login, bank, db_session):
    from app.services import placement as placement_service

    headers = register_and_login()
    done = start(client, headers).json()["attempt_id"]
    submit(client, headers, done)
    completed = db_session.get(PlacementResult, done)

    placement_service._discard_stale_in_progress(db_session, completed)  # gọi nhầm với lượt đã nộp

    assert statuses(db_session).get(done) == "completed"


# ---------- 2. apply chỉ với lượt hoàn thành mới nhất ----------


def test_apply_older_completed_attempt_is_superseded(client, register_and_login, bank):
    headers = register_and_login()
    older = start(client, headers).json()["attempt_id"]
    submit(client, headers, older)
    newer = start(client, headers).json()["attempt_id"]
    submit(client, headers, newer)

    response = client.post(f"{ATTEMPTS}/{older}/apply", headers=headers)

    assert response.status_code == 409 and response.json()["error"]["code"] == "placement_superseded"
    assert client.get(f"{ATTEMPTS}/{older}", headers=headers).json()["result"]["applied_at"] is None


def test_apply_latest_completed_attempt_is_idempotent(client, register_and_login, bank):
    headers = register_and_login()
    older = start(client, headers).json()["attempt_id"]
    submit(client, headers, older)
    newer = start(client, headers).json()["attempt_id"]
    submit(client, headers, newer)

    first = client.post(f"{ATTEMPTS}/{newer}/apply", headers=headers)
    second = client.post(f"{ATTEMPTS}/{newer}/apply", headers=headers)

    assert first.status_code == second.status_code == 200
    assert first.json()["current_level_code"] == second.json()["current_level_code"]


def test_in_progress_newer_attempt_does_not_supersede_completed(client, register_and_login, bank):
    headers = register_and_login()
    done = start(client, headers).json()["attempt_id"]
    submit(client, headers, done)
    start(client, headers)  # đang làm lượt mới nhưng CHƯA nộp

    assert client.post(f"{ATTEMPTS}/{done}/apply", headers=headers).status_code == 200
