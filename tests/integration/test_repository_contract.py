import re

import pytest

from domain.models import PremiumMember, Trainer, WorkoutClass, build_member
from repositories.database import create_session_factory
from repositories.in_memory import InMemoryGymRepository
from repositories.sql_repository import SqlGymRepository


@pytest.fixture
def sql_repo(engine, clean_tables):
    """A PostgreSQL repository with its own session, on empty tables."""
    session = create_session_factory(engine)()
    yield SqlGymRepository(session)
    session.close()


@pytest.fixture(params=["memory", pytest.param("sql", marks=pytest.mark.integration)])
def repo(request):
    """Every test below runs twice: once per repository implementation."""
    if request.param == "memory":
        return InMemoryGymRepository()
    return request.getfixturevalue("sql_repo")


def add_member(repo, member_id: str, name: str = "Member", member_type: str = "BASIC"):
    repo.save_member(build_member(member_id, name, member_type))


#  ids
def test_generated_ids_have_the_documented_format(repo):
    assert re.fullmatch(r"m-[0-9a-f]{8}", repo.next_member_id())
    assert re.fullmatch(r"c-[0-9a-f]{8}", repo.next_class_id())
    assert re.fullmatch(r"t-[0-9a-f]{8}", repo.next_trainer_id())


#  members
def test_saved_member_can_be_read_back(repo):
    add_member(repo, "m-1", "Vera", "PREMIUM")

    member = repo.get_member("m-1")

    assert (member.id, member.name, member.type_name) == ("m-1", "Vera", "PREMIUM")
    assert isinstance(member, PremiumMember)


def test_unknown_records_are_returned_as_none(repo):
    assert repo.get_member("m-none") is None
    assert repo.get_class("c-none") is None
    assert repo.get_trainer("t-none") is None


def test_reads_return_independent_objects(repo):
    add_member(repo, "m-1", "Vera")

    first = repo.get_member("m-1")
    first.name = "Tampered"  # changing the object we received ...

    assert repo.get_member("m-1").name == "Vera"  # ... does not change what is stored
    assert repo.get_member("m-1") is not repo.get_member("m-1")


def test_saving_an_existing_member_replaces_it(repo):
    add_member(repo, "m-1", "Vera", "BASIC")
    add_member(repo, "m-1", "Vera S.", "PREMIUM")  # same id, new name and new type

    member = repo.get_member("m-1")

    assert (member.name, member.type_name) == ("Vera S.", "PREMIUM")
    assert len(repo.list_members()) == 1


def test_list_members_returns_every_member(repo):
    for number in range(3):
        add_member(repo, f"m-{number}", f"Member {number}")

    assert sorted(member.id for member in repo.list_members()) == ["m-0", "m-1", "m-2"]


#  classes
def test_saved_class_keeps_name_capacity_and_trainer(repo):
    repo.save_trainer(Trainer("t-1", "Anna"))
    repo.save_class(WorkoutClass("c-1", "Yoga", 5, trainer_id="t-1"))

    workout = repo.get_class("c-1")

    assert (workout.name, workout.max_capacity, workout.trainer_id) == ("Yoga", 5, "t-1")
    assert workout.enrolled_count == 0


def test_saved_roster_is_stored_with_the_class(repo):
    add_member(repo, "m-1")
    add_member(repo, "m-2")
    repo.save_class(WorkoutClass("c-1", "Yoga", 5, enrolled_member_ids=["m-1", "m-2"]))

    assert sorted(repo.get_class("c-1").enrolled_members_ids) == ["m-1", "m-2"]


def test_saving_a_changed_roster_adds_and_removes_bookings(repo):
    for member_id in ("m-1", "m-2", "m-3"):
        add_member(repo, member_id)
    repo.save_class(WorkoutClass("c-1", "Yoga", 5, enrolled_member_ids=["m-1", "m-2"]))

    workout = repo.get_class("c-1")
    workout.unenroll("m-1")
    workout.enroll("m-3")
    repo.save_class(workout)

    assert sorted(repo.get_class("c-1").enrolled_members_ids) == ["m-2", "m-3"]


def test_count_bookings_of_member_spans_all_classes(repo):
    add_member(repo, "m-1")
    add_member(repo, "m-2")
    repo.save_class(WorkoutClass("c-1", "A", 5, enrolled_member_ids=["m-1"]))
    repo.save_class(WorkoutClass("c-2", "B", 5, enrolled_member_ids=["m-1", "m-2"]))
    repo.save_class(WorkoutClass("c-3", "C", 5))

    assert repo.count_bookings_of_member("m-1") == 2
    assert repo.count_bookings_of_member("m-2") == 1
    assert repo.count_bookings_of_member("m-none") == 0


def test_deleting_a_member_removes_their_bookings(repo):
    add_member(repo, "m-1")
    add_member(repo, "m-2")
    repo.save_class(WorkoutClass("c-1", "Yoga", 5, enrolled_member_ids=["m-1", "m-2"]))

    repo.delete_member("m-1")

    assert repo.get_member("m-1") is None
    assert repo.get_class("c-1").enrolled_members_ids == ("m-2",)
    assert repo.count_bookings_of_member("m-1") == 0


def test_deleting_a_class_removes_it_and_its_bookings(repo):
    add_member(repo, "m-1")
    repo.save_class(WorkoutClass("c-1", "A", 5, enrolled_member_ids=["m-1"]))
    repo.save_class(WorkoutClass("c-2", "B", 5, enrolled_member_ids=["m-1"]))

    repo.delete_class("c-1")

    assert repo.get_class("c-1") is None
    assert repo.count_bookings_of_member("m-1") == 1  # only the booking in c-2 is left
    assert repo.get_member("m-1") is not None  # the member is not affected


#  trainers
def test_saving_an_existing_trainer_replaces_it(repo):
    repo.save_trainer(Trainer("t-1", "Anna"))
    repo.save_trainer(Trainer("t-1", "Anna K."))

    assert repo.get_trainer("t-1").name == "Anna K."
    assert [trainer.id for trainer in repo.list_trainers()] == ["t-1"]


def test_count_classes_of_trainer(repo):
    repo.save_trainer(Trainer("t-1", "Anna"))
    repo.save_trainer(Trainer("t-2", "Boris"))
    repo.save_class(WorkoutClass("c-1", "A", 5, trainer_id="t-1"))
    repo.save_class(WorkoutClass("c-2", "B", 5, trainer_id="t-1"))
    repo.save_class(WorkoutClass("c-3", "C", 5, trainer_id="t-2"))
    repo.save_class(WorkoutClass("c-4", "D", 5))

    assert repo.count_classes_of_trainer("t-1") == 2
    assert repo.count_classes_of_trainer("t-2") == 1
    assert repo.count_classes_of_trainer("t-none") == 0


def test_deleting_a_trainer_without_classes_removes_them(repo):
    repo.save_trainer(Trainer("t-1", "Anna"))

    repo.delete_trainer("t-1")

    assert repo.get_trainer("t-1") is None


#  read model
def test_class_details_include_trainer_and_members(repo):
    repo.save_trainer(Trainer("t-1", "Anna"))
    add_member(repo, "m-1", "Vera", "PREMIUM")
    add_member(repo, "m-2", "Sam", "BASIC")
    repo.save_class(WorkoutClass("c-1", "Yoga", 5, enrolled_member_ids=["m-1", "m-2"], trainer_id="t-1"))
    repo.save_class(WorkoutClass("c-2", "Open gym", 5))

    details = {item.workout_class.id: item for item in repo.list_class_details()}

    assert details["c-1"].trainer.name == "Anna"
    assert {member.id: member.type_name for member in details["c-1"].members} == {
        "m-1": "PREMIUM",
        "m-2": "BASIC",
    }
    assert details["c-1"].workout_class.enrolled_count == 2
    assert details["c-2"].trainer is None
    assert details["c-2"].members == ()


# locking and transactions
def test_locking_reads_return_the_same_data(repo):
    add_member(repo, "m-1", "Vera")
    repo.save_trainer(Trainer("t-1", "Anna"))
    repo.save_class(WorkoutClass("c-1", "Yoga", 5, enrolled_member_ids=["m-1"], trainer_id="t-1"))

    assert repo.get_member("m-1", for_update=True).name == "Vera"
    assert repo.get_trainer("t-1", for_update=True).name == "Anna"
    assert repo.get_class("c-1", for_update=True).enrolled_members_ids == ("m-1",)


def test_work_inside_a_transaction_is_stored(repo):
    with repo.transaction():
        add_member(repo, "m-1", "Vera")

    assert repo.get_member("m-1") is not None