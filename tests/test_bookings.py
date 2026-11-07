import pytest

from domain.exceptions import NotFoundError, RuleViolationError, ValidationError
from services.gym_service import GymService


# book
def test_successful_booking(service: GymService):
    member = service.create_member("Vera", "PREMIUM")
    workout = service.create_class("Morning Yoga", 5)

    booked = service.book_class(member.id, workout.id)

    assert booked.is_enrolled(member.id)
    assert service.get_class(workout.id).enrolled_count == 1


def test_basic_member_is_limited_to_one_booking(service: GymService):
    member = service.create_member("John", "BASIC")
    yoga = service.create_class("Yoga", 5)
    boxing = service.create_class("Boxing", 5)
    service.book_class(member.id, yoga.id)

    with pytest.raises(RuleViolationError, match="booking limit"):
        service.book_class(member.id, boxing.id)

    assert not service.get_class(boxing.id).is_enrolled(member.id)  # nothing half-booked


def test_premium_member_may_book_three_but_not_four(service: GymService):
    # the 3rd booking succeeds, the 4th is rejected
    member = service.create_member("Vera", "PREMIUM")
    classes = [service.create_class(f"Class {i}", 5) for i in range(4)]

    for workout in classes[:3]:
        service.book_class(member.id, workout.id)

    with pytest.raises(RuleViolationError, match="booking limit"):
        service.book_class(member.id, classes[3].id)


def test_booking_a_full_class_is_rejected(service: GymService):
    workout = service.create_class("Exclusive Yoga", 1)
    first = service.create_member("Vincent", "PREMIUM")
    second = service.create_member("Vera", "PREMIUM")
    service.book_class(first.id, workout.id)

    with pytest.raises(RuleViolationError, match="is full"):
        service.book_class(second.id, workout.id)

    assert service.get_class(workout.id).enrolled_count == 1  # roster unchanged


def test_double_booking_is_rejected(service: GymService):
    member = service.create_member("Vera", "PREMIUM")
    workout = service.create_class("Yoga", 5)
    service.book_class(member.id, workout.id)

    with pytest.raises(RuleViolationError, match="already booked"):
        service.book_class(member.id, workout.id)

    assert service.get_class(workout.id).enrolled_count == 1


def test_booking_unknown_member_raises_not_found(service: GymService):
    workout = service.create_class("Yoga", 5)

    with pytest.raises(NotFoundError):
        service.book_class("m-doesnotexist", workout.id)


def test_booking_unknown_class_raises_not_found(service: GymService):
    member = service.create_member("Vera", "BASIC")

    with pytest.raises(NotFoundError):
        service.book_class(member.id, "c-doesnotexist")


@pytest.mark.parametrize("member_id, class_id", [(None, "c-1"), ("m-1", None), (1, 2)])
def test_booking_with_non_string_ids_is_rejected(service: GymService, member_id, class_id):
    with pytest.raises(ValidationError):
        service.book_class(member_id, class_id)


def test_deleting_a_class_frees_the_members_allowance(service: GymService):
    member = service.create_member("John", "BASIC")  # limit of 1
    yoga = service.create_class("Yoga", 5)
    boxing = service.create_class("Boxing", 5)
    service.book_class(member.id, yoga.id)

    service.delete_class(yoga.id)

    service.book_class(member.id, boxing.id)  # allowed again: the old booking is gone
    assert service.get_class(boxing.id).is_enrolled(member.id)


# cancel
def test_cancel_booking_frees_the_seat(service: GymService):
    workout = service.create_class("Yoga", 1)
    first = service.create_member("First", "BASIC")
    second = service.create_member("Second", "BASIC")
    service.book_class(first.id, workout.id)

    updated = service.cancel_booking(first.id, workout.id)

    assert updated.enrolled_count == 0
    service.book_class(second.id, workout.id)  # the freed seat can be taken
    assert service.get_class(workout.id).is_enrolled(second.id)


def test_cancel_booking_frees_the_members_allowance(service: GymService):
    member = service.create_member("John", "BASIC")  # limit of 1
    yoga = service.create_class("Yoga", 5)
    boxing = service.create_class("Boxing", 5)
    service.book_class(member.id, yoga.id)

    service.cancel_booking(member.id, yoga.id)

    service.book_class(member.id, boxing.id)  # allowed again after cancelling
    assert service.get_class(boxing.id).is_enrolled(member.id)


def test_cancel_when_not_enrolled_is_rejected(service: GymService):
    member = service.create_member("Vera", "BASIC")
    workout = service.create_class("Yoga", 5)

    with pytest.raises(RuleViolationError, match="not enrolled"):
        service.cancel_booking(member.id, workout.id)


def test_cancel_with_unknown_member_or_class_raises_not_found(service: GymService):
    member = service.create_member("Vera", "BASIC")
    workout = service.create_class("Yoga", 5)

    with pytest.raises(NotFoundError):
        service.cancel_booking("m-doesnotexist", workout.id)
    with pytest.raises(NotFoundError):
        service.cancel_booking(member.id, "c-doesnotexist")


def test_cancel_with_non_string_ids_is_rejected(service: GymService):
    with pytest.raises(ValidationError):
        service.cancel_booking(None, "c-1")