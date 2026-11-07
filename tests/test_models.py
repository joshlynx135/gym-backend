import pytest

from domain.exceptions import RuleViolationError
from domain.models import BasicMember, Member, PremiumMember, WorkoutClass


# members
def test_member_types_behave_differently():
    assert BasicMember("m-1", "A").get_max_bookings() == 1
    assert PremiumMember("m-2", "B").get_max_bookings() == 3


def test_member_to_dict_exposes_clean_type_label():
    # Regression test: the API once leaked the Python class name "BasicMember"
    data = BasicMember("m-1", "Vincent").to_dict()

    assert data == {"id": "m-1", "name": "Vincent", "type": "BASIC", "max_bookings": 1}


def test_abstract_member_cannot_be_instantiated():
    with pytest.raises(TypeError):
        Member("m-1", "Nobody")  # Member is only a blueprint for Basic/Premium


# workout class
def test_enroll_adds_member_and_updates_count():
    workout = WorkoutClass("c-1", "Yoga", 2)

    workout.enroll("m-1")

    assert workout.is_enrolled("m-1")
    assert workout.enrolled_count == 1
    assert workout.to_dict() == {"id": "c-1", "name": "Yoga", "max_capacity": 2, "enrolled": 1}


def test_class_becomes_full_exactly_at_capacity():
    workout = WorkoutClass("c-1", "Yoga", 2)

    workout.enroll("m-1")
    assert not workout.is_full()   # 1 of 2: still room
    workout.enroll("m-2")
    assert workout.is_full()       # 2 of 2: full


def test_enrolling_into_full_class_is_rejected():
    workout = WorkoutClass("c-1", "Yoga", 1)
    workout.enroll("m-1")

    with pytest.raises(RuleViolationError, match="is full"):
        workout.enroll("m-2")

    assert workout.enrolled_count == 1  # roster unchanged


def test_double_enrollment_is_rejected():
    workout = WorkoutClass("c-1", "Yoga", 5)
    workout.enroll("m-1")

    with pytest.raises(RuleViolationError, match="already booked"):
        workout.enroll("m-1")

    assert workout.enrolled_count == 1


def test_unenroll_removes_member():
    workout = WorkoutClass("c-1", "Yoga", 5)
    workout.enroll("m-1")

    workout.unenroll("m-1")

    assert not workout.is_enrolled("m-1")
    assert workout.enrolled_count == 0


def test_unenroll_when_not_enrolled_is_rejected():
    workout = WorkoutClass("c-1", "Yoga", 5)

    with pytest.raises(RuleViolationError, match="not enrolled"):
        workout.unenroll("m-1")


def test_resize_below_enrollment_is_rejected_and_changes_nothing():
    workout = WorkoutClass("c-1", "Yoga", 3)
    workout.enroll("m-1")
    workout.enroll("m-2")

    with pytest.raises(RuleViolationError, match="Cannot lower capacity"):
        workout.resize(1)

    assert workout.max_capacity == 3  # untouched


def test_resize_to_exactly_current_enrollment_is_allowed():
    workout = WorkoutClass("c-1", "Yoga", 3)
    workout.enroll("m-1")
    workout.enroll("m-2")

    workout.resize(2)  # boundary: capacity == enrolled count

    assert workout.max_capacity == 2
    assert workout.is_full()


def test_roster_is_read_only_from_outside():
    workout = WorkoutClass("c-1", "Yoga", 5)
    workout.enroll("m-1")

    # returns an immutable tuple, so outside code can't sneak members in
    with pytest.raises(AttributeError):
        workout.enrolled_members_ids.append("m-999")
    with pytest.raises(AttributeError):
        workout.enrolled_members_ids = ()