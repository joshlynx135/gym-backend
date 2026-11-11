import pytest

from domain.exceptions import NotFoundError, RuleViolationError, ValidationError
from services.gym_service import GymService


# create
def test_create_class_trims_name_and_starts_empty(service: GymService):
    workout = service.create_class("  Morning Yoga  ", 5)

    assert workout.name == "Morning Yoga"
    assert workout.max_capacity == 5
    assert workout.enrolled_count == 0
    assert workout.id.startswith("c-")


def test_create_class_accepts_minimum_capacity_of_one(service: GymService):
    # Boundary, 1 is the smallest valid capacity
    assert service.create_class("Private Session", 1).max_capacity == 1


@pytest.mark.parametrize("bad_name", ["", "   ", None, 42])
def test_create_class_rejects_invalid_name(service: GymService, bad_name):
    with pytest.raises(ValidationError):
        service.create_class(bad_name, 5)

    assert service.list_classes() == []  # a failed create must store nothing


@pytest.mark.parametrize("bad_capacity", [0, -1, "5", 5.5, True, None])
def test_create_class_rejects_invalid_capacity(service: GymService, bad_capacity):
    # Includes True
    with pytest.raises(ValidationError):
        service.create_class("Yoga", bad_capacity)

    assert service.list_classes() == []


# get
def test_get_class_returns_stored_class(service: GymService):
    created = service.create_class("Yoga", 5)

    fetched = service.get_class(created.id)

    assert fetched.id == created.id
    assert fetched.name == "Yoga"
    assert fetched.max_capacity == 5


def test_get_unknown_class_raises_not_found(service: GymService):
    with pytest.raises(NotFoundError):
        service.get_class("c-doesnotexist")


# list
def test_list_classes_filters_by_min_capacity_inclusively(service: GymService):
    service.create_class("Small", 5)
    service.create_class("Medium", 10)
    service.create_class("Large", 20)

    assert len(service.list_classes()) == 3
    assert {c.name for c in service.list_classes(min_capacity=10)} == {"Medium", "Large"}  # 10 itself is included
    assert service.list_classes(min_capacity=21) == []


@pytest.mark.parametrize("bad_filter", ["10", 2.5, True])
def test_list_classes_rejects_invalid_filter(service: GymService, bad_filter):
    with pytest.raises(ValidationError):
        service.list_classes(min_capacity=bad_filter)


# update
def test_update_class_name_and_capacity(service: GymService):
    workout = service.create_class("Yoga", 5)

    updated = service.update_class(workout.id, new_name="  Hot Yoga ", new_capacity=8)

    assert updated.name == "Hot Yoga"
    assert updated.max_capacity == 8


def test_update_class_with_no_fields_is_rejected(service: GymService):
    workout = service.create_class("Yoga", 5)

    with pytest.raises(ValidationError, match="At least one field"):
        service.update_class(workout.id)


def test_update_unknown_class_raises_not_found(service: GymService):
    with pytest.raises(NotFoundError):
        service.update_class("c-doesnotexist", new_name="X")


def test_cannot_lower_capacity_below_enrollment(service: GymService):
    workout = service.create_class("Yoga", 3)
    for name in ("A", "B"):
        service.book_class(service.create_member(name, "BASIC").id, workout.id)

    with pytest.raises(RuleViolationError, match="Cannot lower capacity"):
        service.update_class(workout.id, new_capacity=1)

    assert service.get_class(workout.id).max_capacity == 3


def test_can_lower_capacity_to_exactly_current_enrollment(service: GymService):
    workout = service.create_class("Yoga", 3)
    for name in ("A", "B"):
        service.book_class(service.create_member(name, "BASIC").id, workout.id)

    updated = service.update_class(workout.id, new_capacity=2)  # boundary: equal to enrolled

    assert updated.max_capacity == 2


def test_failed_class_update_changes_nothing(service: GymService):
    # a valid new name must NOT be applied if the capacity change is rejected
    workout = service.create_class("Yoga", 3)
    for name in ("A", "B"):
        service.book_class(service.create_member(name, "BASIC").id, workout.id)

    with pytest.raises(RuleViolationError):
        service.update_class(workout.id, new_name="Renamed", new_capacity=1)

    unchanged = service.get_class(workout.id)
    assert unchanged.name == "Yoga"
    assert unchanged.max_capacity == 3


def test_invalid_capacity_does_not_apply_valid_name(service: GymService):
    workout = service.create_class("Yoga", 3)

    with pytest.raises(ValidationError):
        service.update_class(workout.id, new_name="Renamed", new_capacity=0)

    assert service.get_class(workout.id).name == "Yoga"


# delete
def test_delete_class_removes_it(service: GymService):
    workout = service.create_class("Yoga", 5)

    service.delete_class(workout.id)

    with pytest.raises(NotFoundError):
        service.get_class(workout.id)


def test_delete_unknown_class_raises_not_found(service: GymService):
    with pytest.raises(NotFoundError):
        service.delete_class("c-doesnotexist")