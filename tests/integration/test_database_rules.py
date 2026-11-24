import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from domain.models import WorkoutClass


def execute(engine, statement: str, **params) -> None:
    """Run one SQL statement in its own transaction (commits when it succeeds)."""
    with engine.begin() as connection:
        connection.execute(text(statement), params)


def scalar(engine, statement: str, **params):
    """Run a SELECT that returns one value and return that value."""
    with engine.connect() as connection:
        return connection.execute(text(statement), params).scalar_one()


def seed_member_and_class(engine) -> None:
    execute(engine, "INSERT INTO members (id, name, type) VALUES ('m-1', 'Vera', 'BASIC')")
    execute(engine, "INSERT INTO classes (id, name, max_capacity) VALUES ('c-1', 'Yoga', 5)")


#  references (FK)
@pytest.mark.parametrize("member_id, class_id", [("m-none", "c-1"), ("m-1", "c-none")])
def test_a_booking_must_reference_an_existing_member_and_class(engine, clean_tables, member_id, class_id):
    seed_member_and_class(engine)

    with pytest.raises(IntegrityError):
        execute(
            engine,
            "INSERT INTO bookings (member_id, class_id) VALUES (:member_id, :class_id)",
            member_id=member_id,
            class_id=class_id,
        )

    assert scalar(engine, "SELECT count(*) FROM bookings") == 0


def test_the_same_member_cannot_be_booked_twice_into_one_class(engine, clean_tables):
    seed_member_and_class(engine)
    execute(engine, "INSERT INTO bookings (member_id, class_id) VALUES ('m-1', 'c-1')")

    with pytest.raises(IntegrityError):
        execute(engine, "INSERT INTO bookings (member_id, class_id) VALUES ('m-1', 'c-1')")


def test_a_class_must_reference_an_existing_trainer(engine, clean_tables):
    with pytest.raises(IntegrityError):
        execute(
            engine,
            "INSERT INTO classes (id, name, max_capacity, trainer_id) VALUES ('c-1', 'Yoga', 5, 't-none')",
        )

    assert scalar(engine, "SELECT count(*) FROM classes") == 0


#  CHECKs
@pytest.mark.parametrize("capacity", [0, -1])
def test_capacity_must_be_positive(engine, clean_tables, capacity):
    with pytest.raises(IntegrityError):
        execute(
            engine,
            "INSERT INTO classes (id, name, max_capacity) VALUES ('c-1', 'Yoga', :capacity)",
            capacity=capacity,
        )


@pytest.mark.parametrize("member_type", ["GOLD", "basic"])
def test_member_type_must_be_basic_or_premium(engine, clean_tables, member_type):
    with pytest.raises(IntegrityError):
        execute(
            engine,
            "INSERT INTO members (id, name, type) VALUES ('m-1', 'Vera', :member_type)",
            member_type=member_type,
        )


#  ON DELETE rules
def test_deleting_a_member_deletes_their_bookings(engine, clean_tables):
    seed_member_and_class(engine)
    execute(engine, "INSERT INTO bookings (member_id, class_id) VALUES ('m-1', 'c-1')")

    execute(engine, "DELETE FROM members WHERE id = 'm-1'")

    assert scalar(engine, "SELECT count(*) FROM bookings") == 0
    assert scalar(engine, "SELECT count(*) FROM classes") == 1  # the class itself is untouched


def test_deleting_a_class_deletes_its_bookings(engine, clean_tables):
    seed_member_and_class(engine)
    execute(engine, "INSERT INTO bookings (member_id, class_id) VALUES ('m-1', 'c-1')")

    execute(engine, "DELETE FROM classes WHERE id = 'c-1'")

    assert scalar(engine, "SELECT count(*) FROM bookings") == 0
    assert scalar(engine, "SELECT count(*) FROM members") == 1  # the member is untouched


def test_a_trainer_with_classes_cannot_be_deleted(engine, clean_tables):
    execute(engine, "INSERT INTO trainers (id, name) VALUES ('t-1', 'Anna')")
    execute(engine, "INSERT INTO classes (id, name, max_capacity, trainer_id) VALUES ('c-1', 'Yoga', 5, 't-1')")

    with pytest.raises(IntegrityError):
        execute(engine, "DELETE FROM trainers WHERE id = 't-1'")

    assert scalar(engine, "SELECT count(*) FROM trainers") == 1


def test_a_trainer_can_be_deleted_once_no_class_uses_them(engine, clean_tables):
    execute(engine, "INSERT INTO trainers (id, name) VALUES ('t-1', 'Anna')")
    execute(engine, "INSERT INTO classes (id, name, max_capacity, trainer_id) VALUES ('c-1', 'Yoga', 5, 't-1')")
    execute(engine, "UPDATE classes SET trainer_id = NULL WHERE id = 'c-1'")

    execute(engine, "DELETE FROM trainers WHERE id = 't-1'")

    assert scalar(engine, "SELECT count(*) FROM trainers") == 0


#  the repository is refused too (safety net)
def test_saving_a_class_with_an_unknown_trainer_is_refused_and_not_stored(make_service):
    repo = make_service().repo

    with pytest.raises(IntegrityError):
        repo.save_class(WorkoutClass("c-1", "Yoga", 5, trainer_id="t-none"))

    assert make_service().repo.get_class("c-1") is None  # a new session sees nothing


def test_saving_a_class_with_an_unknown_member_is_refused_and_not_stored(make_service):
    repo = make_service().repo

    with pytest.raises(IntegrityError):
        repo.save_class(WorkoutClass("c-1", "Yoga", 5, enrolled_member_ids=["m-none"]))

    assert make_service().repo.get_class("c-1") is None