"""
FILE: src/voltsentry/db/migrations/env.py
PATH: voltsentry/src/voltsentry/db/migrations/env.py
DESCRIPTION: Alembic migration environment with dynamic SQLite path and render batch mode support.
"""

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

from voltsentry.db.models import Base
from voltsentry.core.constants import DB_PATH, DATA_DIR

# Alembic Config object
config = context.config

# Ensure data directory exists before running migrations
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Set database URL dynamically from centralized constants / .env
config.set_main_option(
    "sqlalchemy.url",
    f"sqlite:///{DB_PATH}"
)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Model metadata reference for autogenerate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # Enables batch mode for SQLite table alterations
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # Enables batch mode for SQLite table alterations
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()