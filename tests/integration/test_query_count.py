import re
from contextlib import contextmanager

import pytest
from sqlalchemy import event


@contextmanager
def count_selects(engine):
    """Collect every SELECT statement the database receives while the block runs."""
    selects = []

    def record(connection, cursor, statement, parameters, context, executemany):
        if re.search(r"\bFROM\b", statement, re.IGNORECASE):
            selects.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    try:
        yield selects
    finally:
        event.remove(engine, "before_cursor_execute", record)


def seed_classes(make_service, class_count: int) -> None:
    """5 trainers, 40 PREMIUM members and class_count classes with 2 bookings each."""
    service = make_service()
    trainers = [service.create_trainer(f"Trainer {i}") for i in range(5)]
    members = [service.create_member(f"Member {i}", "PREMIUM") for i in range(40)]
    for number in range(class_count):
        workout = service.create_class(f"Class {number}", 10, trainer_id=trainers[number % 5].id)
        for offset in (0, 1):
            # No member exceeds the PREMIUM limit of 3 bookings, even with 50 classes
            service.book_class(members[(2 * number + offset) % 40].id, workout.id)


@pytest.mark.parametrize("class_count", [10, 50])
def test_class_details_need_two_queries_whatever_the_list_size(make_service, engine, class_count):
    seed_classes(make_service, class_count)
    service = make_service()

    with count_selects(engine) as selects:
        details = service.list_class_details()

    assert len(details) == class_count
    assert all(item.trainer is not None and len(item.members) == 2 for item in details)
    # One query for the classes with their trainers (a join), one for the members of all
    # those classes. Loading the related data class by class would need
    # 1 + 2 * class_count queries: 21 for 10 classes, 101 for 50.
    assert len(selects) == 2


@pytest.mark.parametrize("class_count", [10, 50])
def test_plain_class_list_needs_two_queries_whatever_the_list_size(make_service, engine, class_count):
    seed_classes(make_service, class_count)
    service = make_service()

    with count_selects(engine) as selects:
        classes = service.list_classes()

    assert len(classes) == class_count
    assert all(workout.enrolled_count == 2 for workout in classes)
    assert len(selects) == 2  # the classes, then the bookings of all of them