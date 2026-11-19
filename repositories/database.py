import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


DEFAULT_DATABASE_URL = "postgresql+psycopg://gym:gym@localhost:5432/gym"

def get_database_url() -> str:
    """Read the connection URL from the environment, so it can change without editing code."""
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)

def create_db_engine(url: str | None = None) -> Engine:
    """Create an engine (connection pool). Called once per application, not per request."""
    # pool_pre_ping=True tests a pooled connection before using it, so a connection
    # closed by a database restart is replaced instead of causing an error.
    return create_engine(url or get_database_url(), 
                         pool_pre_ping=True,
                         # Seconds to wait for a new connection. Fail fast instead of hanging.
                        connect_args={"connect_timeout": 5},)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Return a callable that creates a new Session bound to the given engine."""
    # expire_on_commit=False keeps loaded objects readable after commit().
    # By default SQLAlchemy marks them "expired" and re-queries on the next access.
    return sessionmaker(bind=engine, expire_on_commit=False)