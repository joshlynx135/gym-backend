from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect, text

from repositories.database import create_db_engine
from repositories.orm import Base
from repositories.schema import downgrade_schema, latest_revision, upgrade_schema

APP_TABLES = {"bookings", "classes", "members", "trainers"}


def test_fresh_install_creates_the_whole_schema(migration_database_url):
    upgrade_schema(migration_database_url)  # an empty database: every migration runs

    engine = create_db_engine(migration_database_url)
    try:
        tables = set(inspect(engine).get_table_names())
        with engine.connect() as connection:
            version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    finally:
        engine.dispose()

    assert APP_TABLES <= tables
    assert version == latest_revision()


def test_upgrade_from_the_first_version_keeps_existing_data(migration_database_url):
    # An installation that predates trainers: schema 0001 with data already in it
    upgrade_schema(migration_database_url, "0001")
    engine = create_db_engine(migration_database_url)
    try:
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO members (id, name, type) VALUES ('m-1', 'Vera', 'PREMIUM')"))
            connection.execute(text("INSERT INTO classes (id, name, max_capacity) VALUES ('c-1', 'Yoga', 5)"))
            connection.execute(text("INSERT INTO bookings (member_id, class_id) VALUES ('m-1', 'c-1')"))

        upgrade_schema(migration_database_url)  # only the missing migrations run

        with engine.connect() as connection:
            member = connection.execute(text("SELECT name, type FROM members WHERE id = 'm-1'")).one()
            workout = connection.execute(text("SELECT name, max_capacity, trainer_id FROM classes")).one()
            bookings = connection.execute(text("SELECT member_id, class_id FROM bookings")).all()
            version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        class_columns = {column["name"] for column in inspector.get_columns("classes")}
    finally:
        engine.dispose()

    # Everything that existed before the upgrade is still there ...
    assert (member.name, member.type) == ("Vera", "PREMIUM")
    assert (workout.name, workout.max_capacity) == ("Yoga", 5)
    assert [(row.member_id, row.class_id) for row in bookings] == [("m-1", "c-1")]
    # ... and the new schema is in place
    assert "trainers" in tables
    assert "trainer_id" in class_columns
    assert workout.trainer_id is None  # existing classes simply have no trainer yet
    assert version == latest_revision()


def test_migrations_can_be_reverted_and_applied_again(migration_database_url):
    upgrade_schema(migration_database_url)
    downgrade_schema(migration_database_url, "base")

    engine = create_db_engine(migration_database_url)
    try:
        tables_after_downgrade = set(inspect(engine).get_table_names())
        upgrade_schema(migration_database_url)
        tables_after_upgrade = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()

    assert tables_after_downgrade.isdisjoint(APP_TABLES)
    assert APP_TABLES <= tables_after_upgrade


def test_orm_models_match_the_migrated_schema(migration_database_url):
    # The ORM classes and the migrations describe the same schema in two places.
    # This test fails when one of them is changed without the other.
    upgrade_schema(migration_database_url)

    engine = create_db_engine(migration_database_url)
    try:
        with engine.connect() as connection:
            differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    finally:
        engine.dispose()

    assert differences == []