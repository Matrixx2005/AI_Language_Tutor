from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Enum, String

import app.models  # noqa: F401
from app.db.base import Base
from app.models import LearnerProfile, User

BACKEND_DIR = Path(__file__).resolve().parents[1]


def test_week2_tables_are_registered():
    assert {"users", "learner_profiles"} <= set(Base.metadata.tables)


def test_no_database_enums_are_used():
    """language_code/level_code là chuỗi mở, không đóng danh sách bằng enum DB."""
    for table in Base.metadata.tables.values():
        for column in table.columns:
            assert not isinstance(column.type, Enum), f"{table.name}.{column.name} dùng Enum"


def test_learner_profile_codes_are_strings_with_erd_defaults():
    table = LearnerProfile.__table__
    expected_defaults = {
        "language_code": "en",
        "current_level_code": "A1",
        "native_language_code": "vi",
    }
    for name, default in expected_defaults.items():
        column = table.c[name]
        assert isinstance(column.type, String)
        assert not column.nullable
        assert column.server_default.arg == default
    assert table.c.learning_goal.nullable


def test_profile_foreign_key_does_not_cascade_delete():
    (foreign_key,) = LearnerProfile.__table__.c.user_id.foreign_keys
    assert foreign_key.column is User.__table__.c.user_id
    assert foreign_key.ondelete == "RESTRICT"


def test_user_email_is_unique_and_repr_hides_personal_data():
    assert User.__table__.c.email.unique
    user = User(email="learner@example.com", password_hash="hash-value")
    assert "learner@example.com" not in repr(user)
    assert "hash-value" not in repr(user)


def test_alembic_has_single_head():
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    heads = ScriptDirectory.from_config(config).get_heads()
    assert len(heads) == 1
