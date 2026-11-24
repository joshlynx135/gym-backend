import pytest

from domain.exceptions import NotFoundError, RuleViolationError, ValidationError
from domain.models import BasicMember, PremiumMember
from services.gym_service import GymService


# create
def test_create_member_normalizes_input(service: GymService):
    member = service.create_member("  Vincent  ", "basic")

    assert member.name == "Vincent"        # whitespace trimmed
    assert member.type_name == "BASIC"     # lowercase input normalized
    assert member.id.startswith("m-")
    assert isinstance(member, BasicMember)


def test_premium_member_has_higher_booking_limit(service: GymService):
    member = service.create_member("Vera", "PREMIUM")

    assert isinstance(member, PremiumMember)
    assert member.get_max_bookings() == 3


@pytest.mark.parametrize("bad_name", ["", "   ", None, 123])
def test_create_member_rejects_invalid_name(service: GymService, bad_name):
    with pytest.raises(ValidationError):
        service.create_member(bad_name, "BASIC")

    assert service.list_members() == []  # a failed create must store nothing


@pytest.mark.parametrize("bad_type", ["GOLD", "", None, 5])
def test_create_member_rejects_invalid_type(service: GymService, bad_type):
    with pytest.raises(ValidationError):
        service.create_member("Vincent", bad_type)

    assert service.list_members() == []


def test_member_ids_are_unique(service: GymService):
    ids = {service.create_member(f"Member {i}", "BASIC").id for i in range(50)}

    assert len(ids) == 50


# get
def test_get_member_returns_stored_member(service: GymService):
    created = service.create_member("Vincent", "BASIC")

    fetched = service.get_member(created.id)

    assert fetched.id == created.id
    assert fetched.name == "Vincent"


def test_get_unknown_member_raises_not_found(service: GymService):
    with pytest.raises(NotFoundError):
        service.get_member("m-doesnotexist")


# list
def test_list_members_filters_by_type(service: GymService):
    service.create_member("A", "BASIC")
    service.create_member("B", "BASIC")
    service.create_member("C", "PREMIUM")

    assert len(service.list_members()) == 3                      # no filter
    assert len(service.list_members("PREMIUM")) == 1
    assert len(service.list_members("basic")) == 2               # filter is case-insensitive


def test_list_members_rejects_invalid_filter(service: GymService):
    with pytest.raises(ValidationError):
        service.list_members("gold")


# update
def test_update_member_name(service: GymService):
    member = service.create_member("Vincent", "BASIC")

    updated = service.update_member(member.id, new_name="  Vince  ")

    assert updated.name == "Vince"
    assert service.get_member(member.id).name == "Vince"


def test_update_member_with_no_fields_is_rejected(service: GymService):
    member = service.create_member("Vincent", "BASIC")

    with pytest.raises(ValidationError, match="At least one field"):
        service.update_member(member.id)


def test_update_unknown_member_raises_not_found(service: GymService):
    with pytest.raises(NotFoundError):
        service.update_member("m-doesnotexist", new_name="X")


def test_update_to_same_type_changes_nothing(service: GymService):
    member = service.create_member("Vincent", "BASIC")

    updated = service.update_member(member.id, new_type="BASIC")

    assert updated.id == member.id
    assert updated.type_name == "BASIC"
    assert updated.name == "Vincent"


def test_upgrade_basic_to_premium_keeps_id_and_bookings(service: GymService):
    member = service.create_member("Vincent", "BASIC")
    workout = service.create_class("Yoga", 5)
    service.book_class(member.id, workout.id)

    upgraded = service.update_member(member.id, new_type="PREMIUM")

    assert upgraded.id == member.id
    assert upgraded.type_name == "PREMIUM"
    assert upgraded.get_max_bookings() == 3
    assert service.get_class(workout.id).is_enrolled(member.id)  # booking survived


def test_downgrade_with_active_bookings_is_blocked(service: GymService):
    member = service.create_member("Vera", "PREMIUM")
    service.book_class(member.id, service.create_class("Yoga", 5).id)
    service.book_class(member.id, service.create_class("Boxing", 5).id)

    with pytest.raises(RuleViolationError, match="exceeds the new limit"):
        service.update_member(member.id, new_type="BASIC")


def test_downgrade_allowed_at_exactly_the_new_limit(service: GymService):
    # Boundary, Basic allows 1 booking, so a member holding exactly 1 may downgrade
    member = service.create_member("Vera", "PREMIUM")
    workout = service.create_class("Yoga", 5)
    service.book_class(member.id, workout.id)

    downgraded = service.update_member(member.id, new_type="BASIC")

    assert downgraded.type_name == "BASIC"
    assert service.get_class(workout.id).is_enrolled(member.id)


def test_failed_update_changes_nothing(service: GymService):
    # if ANY part of an update fails, NO part of it may be applied
    member = service.create_member("Vera", "PREMIUM")
    service.book_class(member.id, service.create_class("Yoga", 5).id)
    service.book_class(member.id, service.create_class("Boxing", 5).id)

    with pytest.raises(RuleViolationError):
        service.update_member(member.id, new_name="Renamed", new_type="BASIC")

    unchanged = service.get_member(member.id)
    assert unchanged.name == "Vera"            # the rename was NOT applied
    assert unchanged.type_name == "PREMIUM"    # the downgrade was NOT applied


def test_update_with_invalid_type_does_not_apply_valid_name(service: GymService):
    member = service.create_member("Vera", "BASIC")

    with pytest.raises(ValidationError):
        service.update_member(member.id, new_name="Renamed", new_type="GOLD")

    assert service.get_member(member.id).name == "Vera"


# delete
def test_delete_member_removes_them(service: GymService):
    member = service.create_member("Vincent", "BASIC")

    service.delete_member(member.id)

    with pytest.raises(NotFoundError):
        service.get_member(member.id)


def test_delete_unknown_member_raises_not_found(service: GymService):
    with pytest.raises(NotFoundError):
        service.delete_member("m-doesnotexist")


def test_delete_member_frees_their_seat(service: GymService):
    workout = service.create_class("Yoga", 1)
    first = service.create_member("First", "BASIC")
    second = service.create_member("Second", "BASIC")
    service.book_class(first.id, workout.id)

    service.delete_member(first.id)

    assert service.get_class(workout.id).enrolled_count == 0
    service.book_class(second.id, workout.id)  # the seat is available again
    assert service.get_class(workout.id).enrolled_count == 1