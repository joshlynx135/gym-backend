import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from domain.exceptions import RuleViolationError


#  rollback
def test_a_failure_during_the_second_write_of_a_transfer_undoes_the_first(make_service, monkeypatch):
    setup = make_service()
    member = setup.create_member("Vera", "BASIC")
    source = setup.create_class("Source", 5)
    target = setup.create_class("Target", 5)
    setup.book_class(member.id, source.id)

    failing = make_service()
    real_save_class = failing.repo.save_class
    calls = []

    def save_class_then_fail(workout_class):
        calls.append(workout_class.id)
        if len(calls) == 2:
            raise RuntimeError("simulated failure during the second write")
        real_save_class(workout_class)  # the first write really reaches the database

    monkeypatch.setattr(failing.repo, "save_class", save_class_then_fail)

    with pytest.raises(RuntimeError):
        failing.transfer_booking(member.id, source.id, target.id)

    assert len(calls) == 2  # the first write ran, then the second one failed

    # A different session sees only committed data: the first write must have been undone
    checking = make_service()
    assert checking.get_class(source.id).is_enrolled(member.id)
    assert checking.get_class(target.id).enrolled_count == 0


def test_a_rejected_transfer_changes_nothing_in_the_database(make_service):
    setup = make_service()
    member = setup.create_member("Vera", "BASIC")
    other = setup.create_member("Sam", "BASIC")
    source = setup.create_class("Source", 5)
    full = setup.create_class("Full", 1)
    setup.book_class(member.id, source.id)
    setup.book_class(other.id, full.id)

    with pytest.raises(RuleViolationError, match="is full"):
        make_service().transfer_booking(member.id, source.id, full.id)

    checking = make_service()
    assert checking.get_class(source.id).is_enrolled(member.id)
    assert checking.get_class(full.id).enrolled_members_ids == (other.id,)


#  concurrency
def test_parallel_bookings_never_exceed_capacity(make_service):
    capacity = 5
    setup = make_service()
    workout = setup.create_class("Yoga", capacity)
    members = [setup.create_member(f"Member {i}", "PREMIUM") for i in range(40)]

    def try_book(member) -> bool:
        try:
            make_service().book_class(member.id, workout.id)  # each call has its own session
            return True
        except RuleViolationError:  # "class is full" for everyone after the first five
            return False

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(try_book, members))

    assert sum(results) == capacity
    assert make_service().get_class(workout.id).enrolled_count == capacity


def test_parallel_bookings_cannot_push_a_member_over_their_limit(make_service):
    setup = make_service()
    member = setup.create_member("Vera", "BASIC")  # limit: 1 booking
    classes = [setup.create_class(f"Class {i}", 5) for i in range(10)]

    def try_book(workout) -> bool:
        try:
            make_service().book_class(member.id, workout.id)
            return True
        except RuleViolationError:  # "booking limit"
            return False

    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(try_book, classes))

    assert sum(results) == 1
    assert make_service().repo.count_bookings_of_member(member.id) == 1


def test_opposite_transfers_at_the_same_time_do_not_deadlock(make_service):
    setup = make_service()
    first = setup.create_member("Vera", "BASIC")
    second = setup.create_member("Sam", "BASIC")
    class_a = setup.create_class("A", 2)
    class_b = setup.create_class("B", 2)
    setup.book_class(first.id, class_a.id)
    setup.book_class(second.id, class_b.id)

    def transfer(barrier, member, from_class, to_class):
        barrier.wait()  # both threads continue at the same moment
        make_service().transfer_booking(member.id, from_class.id, to_class.id)

    for round_number in range(15):
        barrier = threading.Barrier(2)
        if round_number % 2 == 0:
            moves = [(first, class_a, class_b), (second, class_b, class_a)]
        else:
            moves = [(first, class_b, class_a), (second, class_a, class_b)]

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(transfer, barrier, *move) for move in moves]
            for future in futures:
                future.result()  # re-raises any error, for example a deadlock reported by PostgreSQL

    checking = make_service()
    assert checking.get_class(class_a.id).enrolled_count == 1
    assert checking.get_class(class_b.id).enrolled_count == 1