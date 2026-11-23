"""Giới hạn đăng nhập sai và đăng ký (đồng hồ giả, DB test)."""
import logging

import pytest
from starlette.requests import Request

from app.core.limits import client_ip, mask_ip

LOGIN = "/api/v1/auth/login"
REGISTER = "/api/v1/auth/register"
PASSWORD = "mat-khau-an-toan"


def register(client, email="learner@example.com", headers=None):
    return client.post(REGISTER, json={"email": email, "password": PASSWORD}, headers=headers or {})


def login(client, email="learner@example.com", password="sai-mat-khau-1", headers=None):
    return client.post(LOGIN, json={"email": email, "password": password}, headers=headers or {})


def test_too_many_failures_per_email_blocks_even_correct_password(client, limited):
    limited(auth_login_fails_per_email=3, auth_login_fails_per_ip=100)
    register(client)
    for _ in range(3):
        assert login(client).status_code == 401

    blocked = login(client, password=PASSWORD)  # đúng mật khẩu vẫn bị chặn trong cửa sổ

    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "auth_rate_limited"
    assert blocked.headers["retry-after"] == "900"


def test_email_case_and_spaces_do_not_bypass_counter(client, limited):
    limited(auth_login_fails_per_email=3, auth_login_fails_per_ip=100)
    register(client)
    for email in ["Learner@Example.com", " LEARNER@example.com ", "learner@EXAMPLE.COM"]:
        assert login(client, email=email).status_code == 401
    assert login(client, email="learner@example.com").status_code == 429


def test_successful_login_resets_email_counter(client, limited):
    limited(auth_login_fails_per_email=3, auth_login_fails_per_ip=100)
    register(client)
    login(client)
    login(client)
    assert login(client, password=PASSWORD).status_code == 200  # xóa bộ đếm
    login(client)
    login(client)
    assert login(client, password=PASSWORD).status_code == 200  # chưa bị chặn: chỉ 2 lần sai mới


def test_window_expiry_allows_again(client, limited):
    clock = limited(auth_login_fails_per_email=2, auth_login_fails_per_ip=100, auth_login_window_seconds=900)
    register(client)
    login(client)
    clock.advance(100)
    login(client)
    first_blocked = login(client, password=PASSWORD)
    assert first_blocked.status_code == 429 and first_blocked.headers["retry-after"] == "800"

    clock.advance(800)

    assert login(client, password=PASSWORD).status_code == 200


def test_ip_limit_applies_across_different_emails(client, limited):
    limited(auth_login_fails_per_email=100, auth_login_fails_per_ip=3)
    for i in range(3):
        assert login(client, email=f"nguoi{i}@example.com").status_code == 401
    assert login(client, email="nguoi-moi@example.com").status_code == 429


def test_unknown_and_existing_email_get_identical_responses_when_blocked(client, limited):
    limited(auth_login_fails_per_email=2, auth_login_fails_per_ip=100)
    register(client)
    for email in ("learner@example.com", "khong-ton-tai@example.com"):
        login(client, email=email)
        login(client, email=email)
    existing = login(client, email="learner@example.com")
    unknown = login(client, email="khong-ton-tai@example.com")

    assert existing.status_code == unknown.status_code == 429
    assert existing.json() == unknown.json()
    assert existing.headers["retry-after"] == unknown.headers["retry-after"]


def test_register_is_limited_per_ip(client, limited):
    limited(auth_register_per_ip_per_hour=2)
    assert register(client, "a@example.com").status_code == 201
    assert register(client, "a@example.com").status_code == 409  # thử trùng email cũng tính
    blocked = register(client, "c@example.com")
    assert blocked.status_code == 429 and blocked.json()["error"]["code"] == "auth_rate_limited"
    assert blocked.headers["retry-after"] == "3600"


def test_forwarded_for_header_is_ignored_by_default(client, limited):
    limited(auth_login_fails_per_email=100, auth_login_fails_per_ip=2, trusted_proxy_count=0)
    login(client, email="a@example.com", headers={"X-Forwarded-For": "1.1.1.1"})
    login(client, email="b@example.com", headers={"X-Forwarded-For": "2.2.2.2"})
    # Đổi header giả mạo không né được giới hạn theo IP.
    assert login(client, email="c@example.com", headers={"X-Forwarded-For": "3.3.3.3"}).status_code == 429


def test_forwarded_for_is_used_only_with_trusted_proxy(client, limited):
    limited(auth_login_fails_per_email=100, auth_login_fails_per_ip=2, trusted_proxy_count=1)
    for _ in range(2):
        login(client, email="a@example.com", headers={"X-Forwarded-For": "1.1.1.1"})
    assert login(client, email="b@example.com", headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 429
    assert login(client, email="b@example.com", headers={"X-Forwarded-For": "2.2.2.2"}).status_code == 401


def test_logs_have_metadata_but_no_email_or_password(client, limited, caplog):
    limited(auth_login_fails_per_email=1, auth_login_fails_per_ip=100)
    caplog.set_level(logging.DEBUG)
    login(client, email="bi-mat@example.com", password="mat-khau-bi-mat-77")
    login(client, email="bi-mat@example.com", password="mat-khau-bi-mat-77")

    assert "rate_limited kind=login_email" in caplog.text
    assert "bi-mat@example.com" not in caplog.text and "mat-khau-bi-mat-77" not in caplog.text


# ---------- Hàm tiện ích ----------


def make_request(peer: str, forwarded: str | None = None) -> Request:
    headers = [(b"x-forwarded-for", forwarded.encode())] if forwarded else []
    return Request({"type": "http", "headers": headers, "client": (peer, 1234)})


@pytest.mark.parametrize(
    ("peer", "forwarded", "trusted", "expected"),
    [
        ("10.0.0.5", "6.6.6.6", 0, "10.0.0.5"),  # mặc định: bỏ qua header
        ("10.0.0.5", "6.6.6.6", 1, "6.6.6.6"),
        ("10.0.0.5", "9.9.9.9, 6.6.6.6", 1, "6.6.6.6"),  # client giả "9.9.9.9" ở đầu chuỗi bị bỏ
        ("10.0.0.5", "9.9.9.9, 6.6.6.6", 2, "9.9.9.9"),
        ("10.0.0.5", "6.6.6.6", 2, "10.0.0.5"),  # thiếu phần tử → IP kết nối
        ("10.0.0.5", "khong-phai-ip", 1, "10.0.0.5"),
    ],
)
def test_client_ip(peer, forwarded, trusted, expected):
    assert client_ip(make_request(peer, forwarded), trusted) == expected


def test_mask_ip():
    assert mask_ip("203.113.5.77") == "203.113.5.x"
    assert mask_ip("2001:db8:85a3:0:0:8a2e:370:7334") == "2001:0db8:85a3:0000:x"
    assert mask_ip("testclient") == "unknown"
