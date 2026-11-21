"""Ví dụ trên /docs luôn hợp lệ; log lỗi có lý do nhưng không có giá trị.

CORS được kiểm tra trong test_cors.py."""
import logging

import pytest

from app.api.routes.auth import LOGIN_EXAMPLES, REGISTER_EXAMPLES
from app.api.routes.profile import PROFILE_UPDATE_EXAMPLES
from app.core.languages import get_language_config
from app.main import create_app
from app.schemas.auth import LoginRequest, RegisterRequest
from app.schemas.profile import ProfileUpdate

ME = "/api/v1/profile/me"


@pytest.mark.parametrize(
    ("model", "examples"),
    [
        (RegisterRequest, REGISTER_EXAMPLES),
        (LoginRequest, LOGIN_EXAMPLES),
        (ProfileUpdate, PROFILE_UPDATE_EXAMPLES),
    ],
)
def test_docs_examples_pass_validation(model, examples):
    english = get_language_config("en")
    for name, example in examples.items():
        parsed = model.model_validate(example["value"])  # lỗi ở đây = ví dụ đã lỗi thời
        level = getattr(parsed, "current_level_code", None)
        assert level is None or english.is_valid_level(level), name


def test_examples_are_published_in_openapi():
    paths = create_app().openapi()["paths"]
    for path, method in [
        ("/api/v1/auth/register", "post"),
        ("/api/v1/auth/login", "post"),
        (ME, "patch"),
    ]:
        content = paths[path][method]["requestBody"]["content"]["application/json"]
        assert content["examples"], path


def test_validation_rejection_is_logged_without_values(client, caplog):
    password = "ngan-1"  # 6 ký tự
    caplog.set_level(logging.INFO, logger="app")

    client.post("/api/v1/auth/register", json={"email": "a@example.com", "password": password})

    assert "422 POST /api/v1/auth/register -> password: value_error" in caplog.text
    assert password not in caplog.text


def test_business_rejection_is_logged_with_code(client, register_and_login, caplog):
    headers = register_and_login()
    caplog.set_level(logging.INFO, logger="app")

    client.patch(ME, headers=headers, json={"current_level_code": "string"})

    assert "422 PATCH /api/v1/profile/me -> invalid_level_code" in caplog.text
    assert '"string"' not in caplog.text
