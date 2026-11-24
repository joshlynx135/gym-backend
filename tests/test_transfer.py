import pytest

from domain.exceptions import NotFoundError, RuleViolationError, ValidationError
from services.gym_service import GymService


def make_booked_member(service: GymService, member_type: str = "BASIC"):
    """A member booked into a fresh source class, plus an empty target class."""
    member = service.create_member("Vera", member_type)
    source = service.create_class("Source", 5)
    target = service.create_class("Target", 5)
    service.book_class(member.id, source.id)
    return member, source, target


# --------------------------------------------------------------------- success
def test_transfer_moves_the_member_between_classes(service: GymService):
    member, source, target = make_booked_member(service)

    moved_from, moved_to = service.transfer_booking(member.id, source.id, target.id)

    assert not moved_from.is_enrolled(member.id)
    assert moved_to.is_enrolled(member.id)
    # The stored state agrees with the returned objects
    assert not service.get_class(source.id).is_enrolled(member.id)
    assert service.get_class(target.id).is_enrolled(member.id)


def test_basic_member_at_their_limit_can_still_transfer(service: GymService):
    # A BASIC member may hold 1 booking. A transfer removes one booking and adds one,
    # so the total stays at the limit and the transfer must be allowed.
    member, source, target = make_booked_member(service, "BASIC")

    service.transfer_booking(member.id, source.id, target.id)

    total = sum(1 for workout in service.list_classes() if workout.is_enrolled(member.id))
    assert total == 1


def test_transfer_does_not_touch_other_members(service: GymService):
    member, source, target = make_booked_member(service)
    other = service.create_member("Other", "BASIC")
    service.book_class(other.id, source.id)

    service.transfer_booking(member.id, source.id, target.id)

    assert service.get_class(source.id).is_enrolled(other.id)
    assert not service.get_class(target.id).is_enrolled(other.id)


# ------------------------------------------- rule violations change nothing
def test_transfer_into_a_full_class_changes_nothing(service: GymService):
    member, source, _ = make_booked_member(service)
    full = service.create_class("Full", 1)
    service.book_class(service.create_member("Other", "BASIC").id, full.id)

    with pytest.raises(RuleViolationError, match="is full"):
        service.transfer_booking(member.id, source.id, full.id)

    assert service.get_class(source.id).is_enrolled(member.id)  # the booking was not lost
    assert service.get_class(full.id).enrolled_count == 1  # the full class is unchanged


def test_transfer_when_not_enrolled_in_source_changes_nothing(service: GymService):
    member = service.create_member("Vera", "BASIC")
    source = service.create_class("Source", 5)
    target = service.create_class("Target", 5)

    with pytest.raises(RuleViolationError, match="not enrolled"):
        service.transfer_booking(member.id, source.id, target.id)

    assert service.get_class(target.id).enrolled_count == 0


def test_transfer_to_a_class_the_member_already_attends_changes_nothing(service: GymService):
    member = service.create_member("Vera", "PREMIUM")
    source = service.create_class("Source", 5)
    target = service.create_class("Target", 5)
    service.book_class(member.id, source.id)
    service.book_class(member.id, target.id)

    with pytest.raises(RuleViolationError, match="already booked"):
        service.transfer_booking(member.id, source.id, target.id)

    assert service.get_class(source.id).is_enrolled(member.id)  # still booked in both
    assert service.get_class(target.id).is_enrolled(member.id)


# ----------------------------------------------------- invalid and unknown input
def test_transfer_to_the_same_class_is_rejected(service: GymService):
    member, source, _ = make_booked_member(service)

    with pytest.raises(ValidationError, match="different"):
        service.transfer_booking(member.id, source.id, source.id)

    assert service.get_class(source.id).is_enrolled(member.id)


def test_transfer_with_unknown_member_is_rejected(service: GymService):
    source = service.create_class("Source", 5)
    target = service.create_class("Target", 5)

    with pytest.raises(NotFoundError):
        service.transfer_booking("m-doesnotexist", source.id, target.id)


def test_transfer_with_unknown_source_class_changes_nothing(service: GymService):
    member, _, target = make_booked_member(service)

    with pytest.raises(NotFoundError):
        service.transfer_booking(member.id, "c-doesnotexist", target.id)

    assert service.get_class(target.id).enrolled_count == 0


def test_transfer_with_unknown_target_class_changes_nothing(service: GymService):
    member, source, _ = make_booked_member(service)

    with pytest.raises(NotFoundError):
        service.transfer_booking(member.id, source.id, "c-doesnotexist")

    assert service.get_class(source.id).is_enrolled(member.id)  # the booking was not lost


@pytest.mark.parametrize(
    "member_id, from_id, to_id",
    [(None, "c-1", "c-2"), ("m-1", None, "c-2"), ("m-1", "c-1", None)],
)
def test_transfer_with_non_string_ids_is_rejected(service: GymService, member_id, from_id, to_id):
    with pytest.raises(ValidationError):
        service.transfer_booking(member_id, from_id, to_id)