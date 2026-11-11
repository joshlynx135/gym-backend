from concurrent.futures import ThreadPoolExecutor

from domain.exceptions import RuleViolationError
from services.gym_service import GymService


# ---------------------------------------------------------- snapshot isolation
def test_returned_member_is_a_copy_not_the_stored_object(service: GymService):
    created = service.create_member("Vera", "BASIC")

    created.name = "Tampered"  # modify what the service handed out

    assert service.get_member(created.id).name == "Vera"  # stored data is untouched


def test_returned_class_is_isolated_from_later_bookings(service: GymService):
    workout = service.create_class("Yoga", 5)
    snapshot = service.get_class(workout.id)
    member = service.create_member("Vera", "BASIC")

    service.book_class(member.id, workout.id)

    assert snapshot.enrolled_count == 0                       # the old snapshot did not change
    assert service.get_class(workout.id).enrolled_count == 1  # a fresh read sees the booking


def test_listed_members_are_copies(service: GymService):
    service.create_member("Vera", "BASIC")

    listed = service.list_members()
    listed[0].name = "Tampered"

    assert service.list_members()[0].name == "Vera"


def test_listed_classes_are_copies(service: GymService):
    service.create_class("Yoga", 5)

    listed = service.list_classes()
    listed[0].max_capacity = 999

    assert service.list_classes()[0].max_capacity == 5


def test_booking_result_is_a_copy(service: GymService):
    member = service.create_member("Vera", "BASIC")
    workout = service.create_class("Yoga", 5)

    booked = service.book_class(member.id, workout.id)
    booked.max_capacity = 999

    assert service.get_class(workout.id).max_capacity == 5


# ------------------------------------------------------------ parallel access
def test_parallel_bookings_never_exceed_capacity(service: GymService):
    capacity = 5
    workout = service.create_class("Yoga", capacity)
    members = [service.create_member(f"Member {i}", "PREMIUM") for i in range(40)]

    def try_book(member) -> bool:
        try:
            service.book_class(member.id, workout.id)
            return True
        except RuleViolationError:  # "class is full" for everyone after the first 5
            return False

    # 40 members try to book the same class at the same time from 16 threads
    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(try_book, members))

    assert sum(results) == capacity                                  # exactly 5 bookings succeeded
    assert service.get_class(workout.id).enrolled_count == capacity  # and the roster agrees