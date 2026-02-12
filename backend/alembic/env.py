"""Alembic environment configuration.

Reads the database DSN from ``src.config.Settings.cloudsql_dsn`` so that
the connection string is managed in a single place via pydantic-settings
(environment variables / .env).

Supports both *online* (connected to a live database) and *offline*
(generate SQL script only) migration modes.  Uses a **synchronous**
engine because Alembic runs as a CLI tool.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from src.config import get_settings

# -- Alembic Config object ---------------------------------------------------
config = context.config

# Interpret the config file for Python logging (unless we are inside tests
# that have already configured logging).
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url with the value from pydantic-settings.
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.cloudsql_dsn)

# No declarative MetaData (we use raw SQL migrations), so target_metadata
# is None.
target_metadata = None


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Generates the SQL statements without connecting to the database.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Creates a synchronous engine and runs each migration inside a
    transaction.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
