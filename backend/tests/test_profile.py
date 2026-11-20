"""Xem/sửa hồ sơ của chính mình (DB test, rollback mỗi test)."""
import pytest

ME = "/api/v1/profile/me"


def test_read_own_profile(client, register_and_login):
    headers = register_and_login()

    response = client.get(ME, headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == "learner@example.com"


def test_update_goal_level_and_name(client, register_and_login):
    headers = register_and_login()

    response = client.patch(
        ME,
        headers=headers,
        json={"learning_goal": "  Giao tiếp khi đi du lịch  ", "current_level_code": "A2", "display_name": "Lan"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["learning_goal"] == "Giao tiếp khi đi du lịch"
    assert body["current_level_code"] == "A2"
    assert body["display_name"] == "Lan"
    assert client.get(ME, headers=headers).json() == body  # đã lưu thật


def test_patch_only_changes_sent_fields_and_null_clears(client, register_and_login):
    headers = register_and_login()
    client.patch(ME, headers=headers, json={"learning_goal": "IELTS", "display_name": "Lan"})

    body = client.patch(ME, headers=headers, json={"learning_goal": None}).json()

    assert body["learning_goal"] is None
    assert body["display_name"] == "Lan"  # không gửi thì không đổi


def test_user_only_changes_own_profile(client, register_and_login):
    headers_a = register_and_login("a@example.com")
    headers_b = register_and_login("b@example.com")

    client.patch(ME, headers=headers_a, json={"learning_goal": "Mục tiêu của A"})

    assert client.get(ME, headers=headers_a).json()["learning_goal"] == "Mục tiêu của A"
    assert client.get(ME, headers=headers_b).json()["learning_goal"] is None


def test_level_must_exist_in_language_config(client, register_and_login):
    headers = register_and_login()

    response = client.patch(ME, headers=headers, json={"current_level_code": "C2"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_level_code"
    assert client.get(ME, headers=headers).json()["current_level_code"] == "A1"


@pytest.mark.parametrize(
    "payload",
    [
        {"current_level_code": None},
        {"email": "khac@example.com"},
        {"language_code": "ja"},
        {"learning_goal": "x" * 1001},
        {"display_name": "   "},
    ],
)
def test_invalid_or_forbidden_updates_are_rejected(client, register_and_login, payload):
    headers = register_and_login()

    response = client.patch(ME, headers=headers, json=payload)
    assert response.status_code == 422


def test_profile_requires_token(client):
    assert client.get(ME).status_code == 401
    assert client.patch(ME, json={"learning_goal": "x"}).status_code == 401
