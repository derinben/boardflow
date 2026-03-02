"""Alembic environment configuration.

Reads DATABASE_URL from the environment (set via .env / direnv).
Imports BggBase.metadata so that `alembic revision --autogenerate`
can detect model changes automatically.

On first run this module also creates the target database if it does
not yet exist (connecting to the `postgres` maintenance DB first).
"""

import os
from urllib.parse import urlparse, urlunparse

from alembic import context
from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import create_engine, engine_from_config, pool, text

# Load .env so the DATABASE_URL is available when running alembic directly.
load_dotenv()

# Import ORM metadata so autogenerate can diff against the live schema.
from db.models import BggBase  # noqa: E402

config = context.config
DATABASE_URL: str = os.environ["DATABASE_URL"]
config.set_main_option("sqlalchemy.url", DATABASE_URL)

target_metadata = BggBase.metadata


def _maintenance_url(db_url: str) -> str:
    """Replace the database name in a URL with 'postgres' (maintenance DB)."""
    parsed = urlparse(db_url)
    return urlunparse(parsed._replace(path="/postgres"))


def _ensure_database(db_url: str) -> None:
    """Create the target database if it does not yet exist.

    Must connect to the maintenance 'postgres' DB because you cannot CREATE
    a database while connected to it.
    """
    parsed = urlparse(db_url)
    db_name = parsed.path.lstrip("/")
    maintenance_url = _maintenance_url(db_url)

    engine = create_engine(maintenance_url, isolation_level="AUTOCOMMIT", poolclass=pool.NullPool)
    with engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": db_name},
        ).fetchone()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
            logger.info(f"Created database '{db_name}'")
        else:
            logger.debug(f"Database '{db_name}' already exists")
    engine.dispose()


def _ensure_schemas(connection) -> None:
    """Create bgg and features schemas if they do not yet exist."""
    connection.execute(text("CREATE SCHEMA IF NOT EXISTS bgg"))
    connection.execute(text("CREATE SCHEMA IF NOT EXISTS features"))
    connection.commit()
    logger.debug("Ensured schemas: bgg, features")


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (generates SQL output)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
    )
    logger.info("Running migrations in offline mode")
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live DB connection."""
    _ensure_database(DATABASE_URL)

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        _ensure_schemas(connection)
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
        )
        logger.info("Running migrations in online mode")
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
