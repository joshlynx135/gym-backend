from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from repositories.database import get_database_url
from repositories.orm import Base

# Alembic's configuration object (values from alembic.ini plus anything set by code)
config = context.config

# Configure logging from alembic.ini so "Running upgrade ..." lines are printed.
# disable_existing_loggers=False keeps our application's own loggers working.
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# The table definitions Alembic can compare against a real database
target_metadata = Base.metadata

if context.is_offline_mode():
    raise RuntimeError("Offline (--sql) mode is not supported in this project.")


def run_migrations() -> None:
    # A URL set by code wins; otherwise DATABASE_URL, otherwise the default from database.py.
    # The placeholder sqlalchemy.url inside alembic.ini is deliberately ignored.
    url = config.attributes.get("database_url") or get_database_url()
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            # One transaction around all pending migrations: all of them apply, or none do
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()  # close the pooled connections


run_migrations()