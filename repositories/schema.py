from pathlib import Path

from alembic import command
from alembic.config import Config

# This file is repositories/schema.py, so two parents up is the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def upgrade_schema(database_url: str) -> None:
    """Bring the database to the newest schema version.

    On an empty database this creates every table. On an existing one it applies only
    the migrations that are still missing, so stored data is kept.
    """
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    # Absolute paths, so it works no matter which directory the app was started from
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    # env.py reads this value (see config.attributes in migrations/env.py)
    config.attributes["database_url"] = database_url
    command.upgrade(config, "head")