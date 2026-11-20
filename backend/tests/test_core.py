import pytest
from pydantic import ValidationError

from app.core import config
from app.core.config import Settings
from app.core.languages import UnknownLanguageError, get_language_config
from app.main import create_app


def test_short_jwt_secret_is_rejected():
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(_env_file=None, jwt_secret="ngan-qua")


def test_app_refuses_to_start_without_jwt_secret(monkeypatch):
    monkeypatch.setattr(config, "get_settings", lambda: Settings(_env_file=None, jwt_secret=None))
    monkeypatch.setattr("app.main.get_settings", config.get_settings)

    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        create_app()


def test_secret_hidden_in_settings_repr():
    settings = Settings(_env_file=None, jwt_secret="s" * 40)
    assert "s" * 40 not in repr(settings)


def test_english_levels_come_from_yaml():
    language = get_language_config("en")
    assert language.level_codes == ("A1", "A2", "B1")
    assert language.default_level_code == "A1"
    assert not language.is_valid_level("C2")


@pytest.mark.parametrize("code", ["xx", "../.env", "EN", "en/../../secret"])
def test_unknown_or_unsafe_language_codes_are_rejected(code):
    with pytest.raises(UnknownLanguageError):
        get_language_config(code)
