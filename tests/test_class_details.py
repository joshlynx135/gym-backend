import pytest

from domain.exceptions import ValidationError
from services.gym_service import GymService


def test_details_include_trainer_and_members(service: GymService):
    trainer = service.create_trainer("Anna")
    workout = service.create_class("Yoga", 5, trainer_id=trainer.id)
    member = service.create_member("Vera", "PREMIUM")
    service.book_class(member.id, workout.id)

    details = service.list_class_details()[0]

    assert details.workout_class.id == workout.id
    assert details.trainer.name == "Anna"
    assert [m.name for m in details.members] == ["Vera"]
    assert details.members[0].type_name == "PREMIUM"


def test_class_without_trainer_or_members_has_empty_details(service: GymService):
    service.create_class("Open gym", 5)

    details = service.list_class_details()[0]

    assert details.trainer is None
    assert details.members == ()


def test_details_to_dict_shape(service: GymService):
    trainer = service.create_trainer("Anna")
    workout = service.create_class("Yoga", 5, trainer_id=trainer.id)
    member = service.create_member("Vera", "BASIC")
    service.book_class(member.id, workout.id)

    data = service.list_class_details()[0].to_dict()

    assert data == {
        "id": workout.id,
        "name": "Yoga",
        "max_capacity": 5,
        "enrolled": 1,
        "trainer_id": trainer.id,
        "trainer": {"id": trainer.id, "name": "Anna"},
        "members": [{"id": member.id, "name": "Vera", "type": "BASIC", "max_bookings": 1}],
    }


def test_details_support_the_same_filters_as_the_plain_list(service: GymService):
    anna = service.create_trainer("Anna")
    boris = service.create_trainer("Boris")
    service.create_class("Small", 5, trainer_id=anna.id)
    service.create_class("Large", 20, trainer_id=anna.id)
    service.create_class("Boxing", 20, trainer_id=boris.id)

    assert {d.workout_class.name for d in service.list_class_details(min_capacity=10)} == {"Large", "Boxing"}
    assert {d.workout_class.name for d in service.list_class_details(trainer_id=anna.id)} == {"Small", "Large"}
    assert {
        d.workout_class.name for d in service.list_class_details(min_capacity=10, trainer_id=anna.id)
    } == {"Large"}


@pytest.mark.parametrize("bad_filter", ["10", 2.5, True])
def test_details_reject_invalid_min_capacity(service: GymService, bad_filter):
    with pytest.raises(ValidationError):
        service.list_class_details(min_capacity=bad_filter)


def test_details_are_copies_not_stored_objects(service: GymService):
    trainer = service.create_trainer("Anna")
    service.create_class("Yoga", 5, trainer_id=trainer.id)

    details = service.list_class_details()[0]
    details.trainer.name = "Tampered"

    assert service.get_trainer(trainer.id).name == "Anna"


def test_deleted_member_disappears_from_details(service: GymService):
    workout = service.create_class("Yoga", 5)
    member = service.create_member("Vera", "BASIC")
    service.book_class(member.id, workout.id)

    service.delete_member(member.id)

    assert service.list_class_details()[0].members == ()