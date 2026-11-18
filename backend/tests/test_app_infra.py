import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_health_returns_ok_without_database():
    response = TestClient(create_app()).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_database_url_escapes_special_characters_in_password():
    settings = Settings(
        _env_file=None,
        postgres_user="tutor",
        postgres_password="p@ss:w/rd#1",
        postgres_host="db.local",
        postgres_port=5433,
        postgres_db="main_db",
        postgres_test_db="test_db",
    )

    url = settings.database_url()
    test_url = settings.database_url(test=True)

    assert url.password == "p@ss:w/rd#1"
    assert url.host == "db.local" and url.port == 5433
    assert url.database == "main_db"
    assert test_url.database == "test_db"
    assert "p@ss" not in repr(url)  # mật khẩu không lộ khi log URL


def test_database_url_requires_password():
    settings = Settings(_env_file=None, postgres_password=None)

    with pytest.raises(RuntimeError, match="POSTGRES_PASSWORD"):
        settings.database_url()


def test_password_is_hidden_in_settings_repr():
    settings = Settings(_env_file=None, postgres_password="super-secret")

    assert "super-secret" not in repr(settings)
