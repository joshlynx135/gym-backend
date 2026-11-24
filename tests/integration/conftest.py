import os
import re

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError

from repositories.database import create_db_engine, create_session_factory
from repositories.schema import upgrade_schema
from repositories.sql_repository import SqlGymRepository
from services.gym_service import GymService

DEFAULT_TEST_DATABASE_URL = "postgresql+psycopg://gym:gym@localhost:5432/gym_test"


def pytest_collection_modifyitems(items):
    """Label every test that uses the database with the 'integration' marker."""
    for item in items:
        if "database_url" in getattr(item, "fixturenames", ()):
            item.add_marker(pytest.mark.integration)


# helpers 
def _database_name(url: str) -> str:
    name = make_url(url).database or ""
    if not re.fullmatch(r"[a-z0-9_]+_test", name):
        raise RuntimeError(f"Refusing to run database tests against {name!r}: the name must end in '_test'.")
    return name


def _admin_engine(url: str):
    # CREATE/DROP DATABASE cannot run inside a transaction, hence AUTOCOMMIT.
    return create_engine(make_url(url).set(database="postgres"), isolation_level="AUTOCOMMIT")


def _create_database_if_missing(url: str) -> None:
    name = _database_name(url)
    admin = _admin_engine(url)
    try:
        with admin.connect() as connection:
            exists = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": name}
            ).scalar()
            if not exists:
                connection.execute(text(f'CREATE DATABASE "{name}"'))
    finally:
        admin.dispose()


def _recreate_database(url: str) -> None:
    name = _database_name(url)
    admin = _admin_engine(url)
    try:
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
            connection.execute(text(f'CREATE DATABASE "{name}"'))
    finally:
        admin.dispose()


# fixtures 
@pytest.fixture(scope="session")
def database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)
    _database_name(url)  # runs the safety check
    return url


@pytest.fixture(scope="session")
def engine(database_url):
    """An engine for the test database whose schema was built by the real migrations."""
    try:
        _create_database_if_missing(database_url)
    except OperationalError:
        pytest.exit(
            "PostgreSQL is not reachable. Start it with: docker compose up -d --wait",
            returncode=2,
        )

    test_engine = create_db_engine(database_url)
    with test_engine.begin() as connection:
        # Start every test run from an empty database
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    upgrade_schema(database_url)  # also proves that a fresh install works
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def clean_tables(engine):
    """Empty all tables. Tests that need an empty database request this fixture."""
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE TABLE bookings, classes, members, trainers"))

@pytest.fixture
def make_service(engine, clean_tables):
    """Return a function that builds a GymService with its own database session.

    Calling it once is like one HTTP request. Calling it again simulates another request,
    which is how a test checks that data was really stored and not just kept in memory.
    """
    session_factory = create_session_factory(engine)
    sessions = []

    def _make() -> GymService:
        session = session_factory()
        sessions.append(session)
        return GymService(SqlGymRepository(session))

    yield _make
    for session in sessions:
        session.close()


@pytest.fixture
def migration_database_url(database_url) -> str:
    """The URL of an empty database that migration tests may build up and tear down."""
    url = make_url(database_url).set(database="gym_migrations_test").render_as_string(hide_password=False)
    _recreate_database(url)
    return url