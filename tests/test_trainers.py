import pytest

from domain.exceptions import NotFoundError, RuleViolationError, ValidationError
from services.gym_service import GymService


# ---------------------------------------------------------- create, read, list
def test_create_trainer_trims_name_and_gets_an_id(service: GymService):
    trainer = service.create_trainer("  Anna  ")

    assert trainer.name == "Anna"
    assert trainer.id.startswith("t-")


@pytest.mark.parametrize("bad_name", ["", "   ", None, 7])
def test_create_trainer_rejects_invalid_name(service: GymService, bad_name):
    with pytest.raises(ValidationError):
        service.create_trainer(bad_name)

    assert service.list_trainers() == []  # a failed create stores nothing


def test_get_trainer_returns_stored_trainer(service: GymService):
    created = service.create_trainer("Anna")

    fetched = service.get_trainer(created.id)

    assert fetched.id == created.id
    assert fetched.name == "Anna"


def test_get_unknown_trainer_raises_not_found(service: GymService):
    with pytest.raises(NotFoundError):
        service.get_trainer("t-doesnotexist")


def test_list_trainers_returns_all_trainers(service: GymService):
    service.create_trainer("Anna")
    service.create_trainer("Boris")

    assert {t.name for t in service.list_trainers()} == {"Anna", "Boris"}


# ---------------------------------------------------------------------- update
def test_update_trainer_name(service: GymService):
    trainer = service.create_trainer("Anna")

    updated = service.update_trainer(trainer.id, new_name="  Anna K.  ")

    assert updated.name == "Anna K."
    assert service.get_trainer(trainer.id).name == "Anna K."


def test_update_trainer_without_fields_is_rejected(service: GymService):
    trainer = service.create_trainer("Anna")

    with pytest.raises(ValidationError, match="At least one field"):
        service.update_trainer(trainer.id)


def test_update_trainer_with_blank_name_changes_nothing(service: GymService):
    trainer = service.create_trainer("Anna")

    with pytest.raises(ValidationError):
        service.update_trainer(trainer.id, new_name="   ")

    assert service.get_trainer(trainer.id).name == "Anna"


def test_update_unknown_trainer_raises_not_found(service: GymService):
    with pytest.raises(NotFoundError):
        service.update_trainer("t-doesnotexist", new_name="X")


# ------------------------------------------------------- classes and trainers
def test_create_class_without_trainer_has_none(service: GymService):
    assert service.create_class("Yoga", 5).trainer_id is None


def test_create_class_with_trainer(service: GymService):
    trainer = service.create_trainer("Anna")

    workout = service.create_class("Yoga", 5, trainer_id=trainer.id)

    assert workout.trainer_id == trainer.id
    assert service.get_class(workout.id).trainer_id == trainer.id


def test_create_class_with_unknown_trainer_stores_nothing(service: GymService):
    with pytest.raises(NotFoundError):
        service.create_class("Yoga", 5, trainer_id="t-doesnotexist")

    assert service.list_classes() == []  # no class without a valid trainer was created


def test_assign_trainer_to_class(service: GymService):
    trainer = service.create_trainer("Anna")
    workout = service.create_class("Yoga", 5)

    updated = service.assign_trainer(workout.id, trainer.id)

    assert updated.trainer_id == trainer.id
    assert service.get_class(workout.id).trainer_id == trainer.id


def test_reassigning_replaces_the_previous_trainer(service: GymService):
    first = service.create_trainer("Anna")
    second = service.create_trainer("Boris")
    workout = service.create_class("Yoga", 5, trainer_id=first.id)

    service.assign_trainer(workout.id, second.id)

    assert service.get_class(workout.id).trainer_id == second.id


def test_assign_unknown_trainer_changes_nothing(service: GymService):
    trainer = service.create_trainer("Anna")
    workout = service.create_class("Yoga", 5, trainer_id=trainer.id)

    with pytest.raises(NotFoundError):
        service.assign_trainer(workout.id, "t-doesnotexist")

    assert service.get_class(workout.id).trainer_id == trainer.id  # still the old trainer


def test_assign_trainer_to_unknown_class_raises_not_found(service: GymService):
    trainer = service.create_trainer("Anna")

    with pytest.raises(NotFoundError):
        service.assign_trainer("c-doesnotexist", trainer.id)


def test_remove_trainer_from_class(service: GymService):
    trainer = service.create_trainer("Anna")
    workout = service.create_class("Yoga", 5, trainer_id=trainer.id)

    updated = service.remove_trainer(workout.id)

    assert updated.trainer_id is None
    assert service.get_class(workout.id).trainer_id is None


def test_remove_trainer_when_none_is_assigned_is_rejected(service: GymService):
    workout = service.create_class("Yoga", 5)

    with pytest.raises(RuleViolationError, match="no trainer"):
        service.remove_trainer(workout.id)


# ------------------------------------------------------------ deleting trainers
def test_cannot_delete_trainer_who_still_has_classes(service: GymService):
    trainer = service.create_trainer("Anna")
    service.create_class("Yoga", 5, trainer_id=trainer.id)

    with pytest.raises(RuleViolationError, match="Cannot delete trainer"):
        service.delete_trainer(trainer.id)

    assert service.get_trainer(trainer.id).name == "Anna"  # still there


def test_trainer_can_be_deleted_once_no_class_uses_them(service: GymService):
    trainer = service.create_trainer("Anna")
    workout = service.create_class("Yoga", 5, trainer_id=trainer.id)
    service.remove_trainer(workout.id)

    service.delete_trainer(trainer.id)

    with pytest.raises(NotFoundError):
        service.get_trainer(trainer.id)


def test_trainer_can_be_deleted_after_their_class_is_deleted(service: GymService):
    trainer = service.create_trainer("Anna")
    workout = service.create_class("Yoga", 5, trainer_id=trainer.id)
    service.delete_class(workout.id)

    service.delete_trainer(trainer.id)

    assert service.list_trainers() == []


def test_delete_trainer_removes_them(service: GymService):
    trainer = service.create_trainer("Anna")

    service.delete_trainer(trainer.id)

    assert service.list_trainers() == []


def test_delete_unknown_trainer_raises_not_found(service: GymService):
    with pytest.raises(NotFoundError):
        service.delete_trainer("t-doesnotexist")


# --------------------------------------------------------------------- filter
def test_list_classes_filters_by_trainer(service: GymService):
    anna = service.create_trainer("Anna")
    boris = service.create_trainer("Boris")
    service.create_class("Yoga", 5, trainer_id=anna.id)
    service.create_class("Pilates", 5, trainer_id=anna.id)
    service.create_class("Boxing", 5, trainer_id=boris.id)
    service.create_class("Open gym", 5)

    assert {c.name for c in service.list_classes(trainer_id=anna.id)} == {"Yoga", "Pilates"}
    assert {c.name for c in service.list_classes(trainer_id=boris.id)} == {"Boxing"}
    assert service.list_classes(trainer_id="t-doesnotexist") == []
    assert len(service.list_classes()) == 4  # no filter returns everything