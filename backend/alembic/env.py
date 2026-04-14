"""Alembic environment configuration.

Uses the app's models and database URL so `alembic revision --autogenerate`
can detect schema changes automatically.
"""

import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Make sure the backend package is importable when running alembic from the
# backend/ directory (the normal usage).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Import all models so Alembic sees every table in metadata.
# Add new model imports here as the project grows.
from app.core.database import Base  # noqa: E402
import app.models.guide  # noqa: F401, E402
import app.models.outfit  # noqa: F401, E402
import app.models.player_alias  # noqa: F401, E402
import app.models.daily_stats  # noqa: F401, E402
import app.models.match_stats  # noqa: F401, E402
import app.models.finished_match  # noqa: F401, E402
import app.models.prediction  # noqa: F401, E402

# Alembic Config object
config = context.config

# Set up logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The metadata object that autogenerate inspects
target_metadata = Base.metadata


def get_url() -> str:
    """Return a *synchronous* DB URL for Alembic.

    Alembic's async runner requires an async URL (postgresql+asyncpg://…),
    but the offline runner needs a sync URL.  We read the same env var the
    app uses so there is a single source of truth.
    """
    from app.core.database import get_database_url

    url = get_database_url()
    # Alembic's async helper expects asyncpg; keep as-is.
    return url


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (SQL script output)."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations against a live async DB connection."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={"statement_cache_size": 0},
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
