"""
ACGS-2 Alembic Environment Configuration
Constitutional Hash: cdd01ef066bc6cf2

Configures Alembic for SSO database migrations.
Supports both offline (SQL generation) and online (direct execution) modes.
"""

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

# Add the parent directories to the path for model imports
# This allows importing from src.core.shared.database and shared.models
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

# Import the declarative base from src.core.shared.database
from src.core.shared.database import Base

# Import all models so they register with the Base.metadata
# This is required for autogenerate to detect table changes
from src.core.shared.models import (  # noqa: F401
    SAMLOutstandingRequest,
    SSOProvider,
    SSORoleMapping,
    User,
)

# Alembic Config object for access to .ini values
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate support
target_metadata = Base.metadata


def get_url() -> str:
    """Get database URL from environment or alembic.ini.

    Priority:
    1. DATABASE_URL environment variable
    2. sqlalchemy.url from alembic.ini

    Returns:
        Database connection URL for synchronous driver
    """
    url = os.getenv("DATABASE_URL")

    if url is None:
        url = config.get_main_option("sqlalchemy.url")

    # Convert async driver URLs to sync for Alembic
    # Alembic runs migrations synchronously
    if url:
        url = url.replace("postgresql+asyncpg://", "postgresql://")
        url = url.replace("sqlite+aiosqlite://", "sqlite://")

    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This generates SQL scripts without connecting to the database.
    Useful for reviewing migrations before applying or for deployment
    pipelines that need raw SQL.

    Calls to context.execute() emit the given string to the script output.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        render_as_batch=True,  # SQLite compatibility
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Creates an engine and connects directly to the database to run
    migrations. This is the standard mode for applying migrations.
    """
    connectable = create_engine(
        get_url(),
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            render_as_batch=True,  # SQLite compatibility for ALTER TABLE
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
