from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _config(database_url: str | None = None) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    if database_url is not None:
        config.attributes["database_url"] = database_url
    return config


def upgrade_schema(database_url: str, revision: str = "head") -> None:
    """Bring the database to a schema version (the newest one by default).

    On an empty database this creates every table. On an existing one it applies only
    the migrations that are still missing, so stored data is kept.
    """
    command.upgrade(_config(database_url), revision)


def downgrade_schema(database_url: str, revision: str) -> None:
    """Revert migrations down to a version ("base" means: remove everything)."""
    command.downgrade(_config(database_url), revision)


def latest_revision() -> str:
    """The id of the newest migration script, read from the migrations folder."""
    head = ScriptDirectory.from_config(_config()).get_current_head()
    if head is None:
        raise RuntimeError("No migrations found.")
    return head