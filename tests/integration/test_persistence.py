import pytest

from domain.exceptions import NotFoundError, RuleViolationError
from repositories.database import create_db_engine, create_session_factory
from repositories.sql_repository import SqlGymRepository
from services.gym_service import GymService


def test_data_written_by_one_request_is_visible_to_the_next(make_service):
    first_request = make_service()
    trainer = first_request.create_trainer("Anna")
    workout = first_request.create_class("Yoga", 5, trainer_id=trainer.id)
    member = first_request.create_member("Vera", "PREMIUM")
    first_request.book_class(member.id, workout.id)

    next_request = make_service()  # a different session, like the next HTTP request

    stored = next_request.get_class(workout.id)
    assert stored.trainer_id == trainer.id
    assert stored.is_enrolled(member.id)
    assert next_request.get_member(member.id).type_name == "PREMIUM"


def test_related_objects_are_loaded_together(make_service):
    writer = make_service()
    trainer = writer.create_trainer("Anna")
    workout = writer.create_class("Yoga", 5, trainer_id=trainer.id)
    for name in ("Vera", "Sam"):
        writer.book_class(writer.create_member(name, "BASIC").id, workout.id)

    details = make_service().list_class_details()[0]

    assert details.trainer.name == "Anna"
    assert sorted(member.name for member in details.members) == ["Sam", "Vera"]
    assert details.workout_class.enrolled_count == 2


def test_data_survives_an_application_restart(make_service, database_url):
    created = make_service().create_member("Vera", "PREMIUM")

    restarted_engine = create_db_engine(database_url)
    try:
        session = create_session_factory(restarted_engine)()
        try:
            restarted_service = GymService(SqlGymRepository(session))
            assert restarted_service.get_member(created.id).name == "Vera"
        finally:
            session.close()
    finally:
        restarted_engine.dispose()


def test_a_failed_create_leaves_nothing_stored(make_service):
    with pytest.raises(NotFoundError):
        make_service().create_class("Ghost", 5, trainer_id="t-none")

    assert make_service().list_classes() == []


def test_deleting_a_member_frees_their_seat_in_the_database(make_service):
    service = make_service()
    workout = service.create_class("Yoga", 5)
    member = service.create_member("Vera", "BASIC")
    service.book_class(member.id, workout.id)

    service.delete_member(member.id)

    checking = make_service()
    assert checking.get_class(workout.id).enrolled_count == 0
    with pytest.raises(NotFoundError):
        checking.get_member(member.id)


def test_deleting_a_class_keeps_its_members(make_service):
    service = make_service()
    workout = service.create_class("Yoga", 5)
    member = service.create_member("Vera", "BASIC")
    service.book_class(member.id, workout.id)

    service.delete_class(workout.id)

    checking = make_service()
    assert checking.list_classes() == []
    assert checking.get_member(member.id).name == "Vera"


def test_a_trainer_in_use_cannot_be_deleted_and_stays_stored(make_service):
    service = make_service()
    trainer = service.create_trainer("Anna")
    service.create_class("Yoga", 5, trainer_id=trainer.id)

    with pytest.raises(RuleViolationError):
        service.delete_trainer(trainer.id)

    assert make_service().get_trainer(trainer.id).name == "Anna"