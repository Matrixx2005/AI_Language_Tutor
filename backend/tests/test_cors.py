from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

DEV_ORIGIN = "http://localhost:5173"


@pytest.fixture
def client_for_environment(monkeypatch: pytest.MonkeyPatch) -> Callable[[str], TestClient]:
    def make_client(environment: str) -> TestClient:
        settings = Settings(
            _env_file=None,
            environment=environment,
            jwt_secret="test-only-secret-that-is-at-least-32-bytes",
        )
        monkeypatch.setattr("app.main.get_settings", lambda: settings)
        return TestClient(create_app())

    return make_client


def test_development_origin_is_allowed(client_for_environment: Callable[[str], TestClient]) -> None:
    with client_for_environment("development") as client:
        response = client.options(
            "/api/v1/profile/me",
            headers={
                "Origin": DEV_ORIGIN,
                "Access-Control-Request-Method": "PATCH",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == DEV_ORIGIN


def test_unknown_origin_gets_no_allow_origin_header(
    client_for_environment: Callable[[str], TestClient],
) -> None:
    with client_for_environment("development") as client:
        response = client.options(
            "/api/v1/profile/me",
            headers={
                "Origin": "https://untrusted.example",
                "Access-Control-Request-Method": "PATCH",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )

    assert "access-control-allow-origin" not in response.headers


def test_configured_origins_override_dev_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
        cors_origins="https://tutor.example.edu.vn/ , https://admin.example.edu.vn",
        jwt_secret="test-only-secret-that-is-at-least-32-bytes",
    )
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    preflight = {"Access-Control-Request-Method": "GET"}

    with TestClient(create_app()) as client:
        allowed = client.options("/health", headers={"Origin": "https://tutor.example.edu.vn", **preflight})
        vite = client.options("/health", headers={"Origin": DEV_ORIGIN, **preflight})

    assert allowed.headers["access-control-allow-origin"] == "https://tutor.example.edu.vn"
    assert "access-control-allow-origin" not in vite.headers  # không còn mặc định dev


def test_wildcard_origin_is_rejected() -> None:
    with pytest.raises(ValueError, match="CORS_ORIGINS"):
        Settings(_env_file=None, cors_origins="*")


def test_cors_is_disabled_outside_development(
    client_for_environment: Callable[[str], TestClient],
) -> None:
    with client_for_environment("production") as client:
        response = client.get("/health", headers={"Origin": DEV_ORIGIN})

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
