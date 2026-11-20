"""Môi trường Alembic. URL DB lấy từ .env qua app.core.config, không ghi trong alembic.ini.

Chạy từ thư mục backend/:
  alembic upgrade head                 # DB chính
  alembic -x db=test upgrade head      # DB test (ai_language_tutor_test)
  alembic upgrade head --sql           # chỉ in SQL, không chạm DB
"""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

import app.models  # noqa: F401  (nạp mọi model vào Base.metadata)
from app.core.config import get_settings
from app.db.base import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url():
    use_test_db = context.get_x_argument(as_dictionary=True).get("db") == "test"
    return get_settings().database_url(test=use_test_db)


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    settings = get_settings()
    # Truyền URL object trực tiếp: tránh lỗi ký tự % trong mật khẩu khi đi qua alembic.ini.
    connectable = create_engine(
        _database_url(),
        poolclass=pool.NullPool,
        connect_args={"connect_timeout": settings.postgres_connect_timeout},
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
