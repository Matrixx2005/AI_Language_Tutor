"""Đăng ký, đăng nhập, xác thực token (DB test, rollback mỗi test)."""
import base64
import json
import logging
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import JWT_ISSUER, create_access_token
from app.models import User

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
ME = "/api/v1/profile/me"
PASSWORD = "mat-khau-an-toan"


def register(client, email="learner@example.com", password=PASSWORD, **extra):
    return client.post(REGISTER, json={"email": email, "password": password, **extra})


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---------- Đăng ký ----------


def test_register_creates_user_and_profile_from_language_config(client):
    response = register(client, email="  New.Learner@Example.COM ", display_name=" Minh ")

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "new.learner@example.com"  # đã chuẩn hóa
    assert body["display_name"] == "Minh"
    assert (body["language_code"], body["current_level_code"], body["native_language_code"]) == (
        "en",
        "A1",
        "vi",
    )
    assert "password" not in json.dumps(body) and "hash" not in json.dumps(body)


def test_password_is_stored_as_argon2id_hash(client, db_session):
    register(client)
    stored = db_session.scalar(select(User.password_hash))
    assert stored.startswith("$argon2id$") and PASSWORD not in stored


def test_register_duplicate_email_is_case_insensitive(client):
    assert register(client).status_code == 201
    response = register(client, email="LEARNER@example.com")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_already_registered"


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"email": "khong-phai-email", "password": PASSWORD}, "email"),
        ({"email": "a@example.com", "password": "ngan"}, "password"),
        ({"email": "a@example.com", "password": "x" * 129}, "password"),
        ({"email": "a@example.com"}, "password"),
        ({"email": "a@example.com", "password": PASSWORD, "is_admin": True}, "is_admin"),
    ],
)
def test_register_rejects_invalid_input(client, payload, field):
    response = client.post(REGISTER, json=payload)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert any(detail["field"] == field for detail in error["details"])


def test_register_rejects_password_equal_to_email(client):
    response = register(client, email="learner@example.com", password="Learner@Example.com")
    assert response.status_code == 422
    (detail,) = response.json()["error"]["details"]
    assert detail["message"] == "Mật khẩu không được trùng với email"  # không còn "Value error, "


def test_password_never_echoed_in_errors_or_logs(client, caplog):
    secret = "bi-mat-khong-duoc-lo-123"
    caplog.set_level(logging.DEBUG)

    responses = [
        client.post(REGISTER, json={"email": "khong-hop-le", "password": secret}),
        client.post(REGISTER, json={"email": "a@example.com", "password": secret, "extra": 1}),
        # Lỗi nằm chính ở ô mật khẩu: FastAPI mặc định trả lại giá trị này trong `input`.
        client.post(REGISTER, json={"email": "a@example.com", "password": secret * 6}),
        client.post(LOGIN, json={"email": "a@example.com", "password": secret * 6}),
        client.post(LOGIN, json={"email": "nobody@example.com", "password": secret}),
    ]
    # Lỗi cấp model (mật khẩu trùng email): `input` mặc định là cả body.
    same_as_email = "bi-mat.trung@example.com"
    responses.append(client.post(REGISTER, json={"email": same_as_email, "password": same_as_email}))

    assert [r.status_code for r in responses] == [422, 422, 422, 422, 401, 422]
    for response in responses[:-1]:
        assert secret not in response.text
    assert '"input"' not in responses[-1].text
    assert secret not in caplog.text


# ---------- Đăng nhập ----------


def test_login_returns_bearer_token(client):
    register(client)
    response = client.post(LOGIN, json={"email": "Learner@Example.com", "password": PASSWORD})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == get_settings().access_token_expire_minutes * 60
    assert client.get(ME, headers=bearer(body["access_token"])).status_code == 200


def test_wrong_password_and_unknown_email_get_identical_errors(client):
    register(client)
    wrong_password = client.post(LOGIN, json={"email": "learner@example.com", "password": "sai-mat-khau"})
    unknown_email = client.post(LOGIN, json={"email": "nobody@example.com", "password": "sai-mat-khau"})

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()
    assert wrong_password.json()["error"]["code"] == "invalid_credentials"


def test_login_upgrades_outdated_password_hash(client, db_session):
    register(client)
    user = db_session.scalar(select(User))
    weak = PasswordHash((Argon2Hasher(time_cost=1, memory_cost=8192, parallelism=1),))
    user.password_hash = weak.hash(PASSWORD)
    db_session.flush()

    assert client.post(LOGIN, json={"email": "learner@example.com", "password": PASSWORD}).status_code == 200
    db_session.refresh(user)
    assert "m=65536,t=3,p=4" in user.password_hash


# ---------- Token ----------


def _payload(user_id: uuid.UUID, **overrides):
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iss": JWT_ISSUER,
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    payload.update(overrides)
    return {key: value for key, value in payload.items() if value is not None}


def _user_id(client, db_session) -> uuid.UUID:
    register(client)
    return db_session.scalar(select(User.user_id))


def _sign(payload, secret=None):
    return jwt.encode(payload, secret or get_settings().require_jwt_secret(), algorithm="HS256")


def test_missing_token_is_rejected(client):
    response = client.get(ME)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"
    assert response.headers["www-authenticate"] == "Bearer"


def test_non_bearer_scheme_is_rejected(client):
    assert client.get(ME, headers={"Authorization": "Basic YWJjOmRlZg=="}).status_code == 401


def test_expired_token_is_rejected(client, db_session):
    user_id = _user_id(client, db_session)
    token, _ = create_access_token(user_id, now=datetime.now(UTC) - timedelta(hours=2))

    response = client.get(ME, headers=bearer(token))
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "token_expired"


@pytest.mark.parametrize(
    "make_token",
    [
        pytest.param(lambda uid: _sign(_payload(uid), secret="x" * 64), id="sai-secret"),
        pytest.param(lambda uid: _sign(_payload(uid, iss="ke-gia-mao")), id="sai-issuer"),
        pytest.param(lambda uid: _sign(_payload(uid, type="refresh")), id="sai-loai-token"),
        pytest.param(lambda uid: _sign(_payload(uid, exp=None)), id="thieu-exp"),
        pytest.param(lambda uid: _sign(_payload(uid, sub="khong-phai-uuid")), id="sub-sai"),
        pytest.param(lambda uid: _sign(_payload(uuid.uuid4())), id="user-khong-ton-tai"),
        pytest.param(lambda uid: "khong.phai.jwt", id="rac"),
    ],
)
def test_invalid_tokens_are_rejected(client, db_session, make_token):
    token = make_token(_user_id(client, db_session))

    response = client.get(ME, headers=bearer(token))
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


def _b64(data: dict) -> str:
    raw = json.dumps(data, default=lambda v: int(v.timestamp())).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def test_alg_none_token_is_rejected(client, db_session):
    user_id = _user_id(client, db_session)
    token = f"{_b64({'alg': 'none', 'typ': 'JWT'})}.{_b64(_payload(user_id))}."

    assert client.get(ME, headers=bearer(token)).status_code == 401


def test_tampered_payload_is_rejected(client, db_session):
    user_id = _user_id(client, db_session)
    header, _, signature = _sign(_payload(user_id)).split(".")
    forged = _b64(_payload(uuid.uuid4()))  # đổi người dùng nhưng giữ chữ ký cũ

    assert client.get(ME, headers=bearer(f"{header}.{forged}.{signature}")).status_code == 401
