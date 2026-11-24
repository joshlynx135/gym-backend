import functools
from typing import Optional

from domain.exceptions import NotFoundError, RuleViolationError, ValidationError
from domain.models import ClassDetails, Member, Trainer, WorkoutClass, build_member
from repositories.base import GymRepository


def transactional(method):
    """Run a service method inside one repository transaction.

    Everything the method saves is committed together when it returns, and rolled back
    together if it raises, so a failed operation never leaves partial changes behind.
    """
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        with self.repo.transaction():
            return method(self, *args, **kwargs)
    return wrapper


class GymService:
    """Business rules for members, classes and bookings.

    The service holds no state and no locks. Each public method loads detached objects
    from the repository, applies the rules to them, and saves the result. When the
    repository is backed by PostgreSQL, one request is one transaction: if a rule fails
    before save_*, nothing has been written.
    """

    def __init__(self, repo: GymRepository) -> None:
        # Injected dependency: the service never creates its own storage
        self.repo = repo

    # ---- Validation helpers (malformed input -> ValidationError -> HTTP 400) ----
    @staticmethod
    def _validate_non_empty_string(value, field_name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValidationError(f"{field_name} must be a non-empty string.")
        return value.strip()

    @staticmethod
    def _validate_capacity(value) -> int:
        # bool is a subclass of int in Python, so True would pass without this check
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValidationError("Capacity must be a positive integer greater than 0.")
        return value

    @staticmethod
    def _validate_member_type(value, label: str = "Type") -> str:
        if not isinstance(value, str) or value.strip().upper() not in ("BASIC", "PREMIUM"):
            raise ValidationError(f"{label} must be either 'BASIC' or 'PREMIUM'.")
        return value.strip().upper()

    @staticmethod
    def _validate_id_pair(member_id, class_id) -> None:
        if not isinstance(member_id, str) or not isinstance(class_id, str):
            raise ValidationError("Both 'member_id' and 'class_id' must be valid strings.")

    # @staticmethod
    # def _build_member(member_id: str, name: str, member_type: str) -> Member:
    #     if member_type == "PREMIUM":
    #         return PremiumMember(member_id, name)
    #     return BasicMember(member_id, name)
    @staticmethod
    def _class_filter(min_capacity, trainer_id):
        """Validate the optional list filters and return a function that tests one class."""
        if min_capacity is not None and (isinstance(min_capacity, bool) or not isinstance(min_capacity, int)):
            raise ValidationError("min_capacity must be an integer.")

        def matches(workout_class: WorkoutClass) -> bool:
            return (
                (min_capacity is None or workout_class.max_capacity >= min_capacity)
                and (trainer_id is None or workout_class.trainer_id == trainer_id)
            )

        return matches

    # ---- Internal helpers ----
    def _find_member(self, member_id: str, *, for_update: bool = False) -> Member:
        member = self.repo.get_member(member_id, for_update=for_update)
        if member is None:
            raise NotFoundError(f"Member with ID {member_id} not found.")
        return member

    def _find_class(self, class_id: str, *, for_update: bool = False) -> WorkoutClass:
        workout_class = self.repo.get_class(class_id, for_update=for_update)
        if workout_class is None:
            raise NotFoundError(f"Class with ID {class_id} not found.")
        return workout_class

    def _find_trainer(self, trainer_id:str, *, for_update: bool = False) -> Trainer:
        trainer = self.repo.get_trainer(trainer_id, for_update=for_update)
        if trainer is None:
            raise NotFoundError(f"Trainer with ID {trainer_id} not found.")
        return trainer
    
    # ---- Members ----
    @transactional
    def create_member(self, name: str, member_type: str) -> Member:
        clean_name = self._validate_non_empty_string(name, "Member name")
        target_type = self._validate_member_type(member_type)

        member = build_member(self.repo.next_member_id(), clean_name, target_type)
        self.repo.save_member(member)
        return member

    @transactional
    def get_member(self, member_id: str) -> Member:
        return self._find_member(member_id)

    @transactional
    def list_members(self, member_type: Optional[str] = None) -> list[Member]:
        members = self.repo.list_members()
        if member_type is not None:
            target = self._validate_member_type(member_type, "Filter type")
            members = [m for m in members if m.type_name == target]
        return members

    @transactional
    def update_member(
        self, member_id: str, new_name: Optional[str] = None, new_type: Optional[str] = None
    ) -> Member:
        member = self._find_member(member_id, for_update=True)
        if new_name is None and new_type is None:
            raise ValidationError("At least one field ('name' or 'type') must be provided for update.")

        # Validate everything first. Nothing has been saved, so a failure changes nothing.
        clean_name = (
            self._validate_non_empty_string(new_name, "Member name")
            if new_name is not None else member.name
        )

        replacement = None
        if new_type is not None:
            target_type = self._validate_member_type(new_type)
            if target_type != member.type_name:
                replacement = build_member(member_id, clean_name, target_type)
                current_bookings = self.repo.count_bookings_of_member(member_id)
                if current_bookings > replacement.get_max_bookings():
                    raise RuleViolationError(
                        f"Cannot change type to {target_type}: member has {current_bookings} active bookings, "
                        f"which exceeds the new limit of {replacement.get_max_bookings()}."
                    )

        updated = replacement if replacement is not None else member
        updated.name = clean_name
        self.repo.save_member(updated)
        return updated

    @transactional
    def delete_member(self, member_id: str) -> None:
        self._find_member(member_id)  # raises NotFoundError if missing
        self.repo.delete_member(member_id)  # the member's bookings are removed too

    # ---- Trainers ----
    @transactional
    def create_trainer(self, name: str) -> Trainer:
        clean_name = self._validate_non_empty_string(name, "Trainer name")

        trainer = Trainer(self.repo.next_trainer_id(), clean_name)
        self.repo.save_trainer(trainer)
        return trainer

    @transactional
    def get_trainer(self, trainer_id: str) -> Trainer:
        return self._find_trainer(trainer_id)

    @transactional
    def list_trainers(self) -> list[Trainer]:
        return self.repo.list_trainers()

    @transactional
    def update_trainer(self, trainer_id: str, new_name: Optional[str] = None) -> Trainer:
        trainer = self._find_trainer(trainer_id, for_update=True)
        if new_name is None:
            raise ValidationError("At least one field ('name') must be provided for update.")

        trainer.name = self._validate_non_empty_string(new_name, "Trainer name")
        self.repo.save_trainer(trainer)
        return trainer

    @transactional
    def delete_trainer(self, trainer_id: str) -> None:
        # Locking the trainer row stops another request from assigning this trainer
        # to a class between our check and our delete
        self._find_trainer(trainer_id, for_update=True)
        class_count = self.repo.count_classes_of_trainer(trainer_id)
        if class_count > 0:
            raise RuleViolationError(
                f"Cannot delete trainer: {class_count} class(es) still use this trainer. "
                "Assign another trainer or remove the trainer from those classes first."
            )
        self.repo.delete_trainer(trainer_id)

    # ---- Workout classes ----
    @transactional
    def create_class(self, name: str, max_capacity: int, trainer_id: Optional[str] = None) -> WorkoutClass:
        clean_name = self._validate_non_empty_string(name, "Class name")
        clean_capacity = self._validate_capacity(max_capacity)

        clean_trainer_id = None
        if trainer_id is not None:
            clean_trainer_id = self._validate_non_empty_string(trainer_id, "Trainer id")
            self._find_trainer(clean_trainer_id, for_update=True)  # 404 if it does not exist

        workout_class = WorkoutClass(
            self.repo.next_class_id(), clean_name, clean_capacity, trainer_id=clean_trainer_id
        )
        self.repo.save_class(workout_class)
        return workout_class
    
    @transactional
    def get_class(self, class_id: str) -> WorkoutClass:
        return self._find_class(class_id)

    @transactional
    def list_classes(
        self, min_capacity: Optional[int] = None, trainer_id: Optional[str] = None
    ) -> list[WorkoutClass]:
        matches = self._class_filter(min_capacity, trainer_id)
        return [workout_class for workout_class in self.repo.list_classes() if matches(workout_class)]

    @transactional
    def list_class_details(
        self, min_capacity: Optional[int] = None, trainer_id: Optional[str] = None
    ) -> list[ClassDetails]:
        matches = self._class_filter(min_capacity, trainer_id)
        return [details for details in self.repo.list_class_details() if matches(details.workout_class)]

    @transactional
    def update_class(
        self, class_id: str, new_name: Optional[str] = None, new_capacity: Optional[int] = None
    ) -> WorkoutClass:
        workout_class = self._find_class(class_id, for_update=True)
        if new_name is None and new_capacity is None:
            raise ValidationError("At least one field ('name' or 'max_capacity') must be provided for update.")

        clean_name = (
            self._validate_non_empty_string(new_name, "Class name")
            if new_name is not None else workout_class.name
        )
        # resize() raises if the new capacity is below the number of bookings.
        # We work on our own copy and have not saved yet, so the stored class is untouched.
        if new_capacity is not None:
            workout_class.resize(self._validate_capacity(new_capacity))

        workout_class.name = clean_name
        self.repo.save_class(workout_class)
        return workout_class

    @transactional
    def delete_class(self, class_id: str) -> None:
        self._find_class(class_id)  # raises NotFoundError if missing
        self.repo.delete_class(class_id)

    # ---- Domain operations ----
    @transactional
    def book_class(self, member_id: str, class_id: str) -> WorkoutClass:
        self._validate_id_pair(member_id, class_id)

        # Lock order is always member first, then class
        member = self._find_member(member_id, for_update=True)
        workout_class = self._find_class(class_id, for_update=True)

        # The class checks "already booked" and "full"; the service checks the member's
        # limit, because that needs a view across ALL classes
        workout_class.ensure_can_enroll(member_id)
        if self.repo.count_bookings_of_member(member_id) >= member.get_max_bookings():
            raise RuleViolationError(f"Member {member.name} has reached their booking limit.")

        workout_class.enroll(member_id)
        self.repo.save_class(workout_class)
        return workout_class

    @transactional
    def cancel_booking(self, member_id: str, class_id: str) -> WorkoutClass:
        self._validate_id_pair(member_id, class_id)

        self._find_member(member_id, for_update=True)
        workout_class = self._find_class(class_id, for_update=True)

        workout_class.unenroll(member_id)  # raises RuleViolationError if not enrolled
        self.repo.save_class(workout_class)
        return workout_class

    @transactional
    def transfer_booking(
        self, member_id: str, from_class_id: str, to_class_id: str
    ) -> tuple[WorkoutClass, WorkoutClass]:
        """Move a member's booking from one class to another, all or nothing."""
        self._validate_id_pair(member_id, from_class_id)
        self._validate_id_pair(member_id, to_class_id)
        if from_class_id == to_class_id:
            raise ValidationError("'from_class_id' and 'to_class_id' must be different classes.")

        self._find_member(member_id, for_update=True)

        # Lock both classes in ascending id order. Every transaction uses the same order,
        # so two opposite transfers (A to B and B to A) can never wait for each other.
        classes = {
            class_id: self._find_class(class_id, for_update=True)
            for class_id in sorted((from_class_id, to_class_id))
        }
        source, target = classes[from_class_id], classes[to_class_id]

        # Both objects are private copies and nothing is saved yet: if either rule raises,
        # no change has been written anywhere
        source.unenroll(member_id)  # raises if the member is not in the source class
        target.enroll(member_id)  # raises if the target is full or already has the member

        self.repo.save_class(source)
        self.repo.save_class(target)  # same transaction as the line above
        return source, target
    
    @transactional
    def assign_trainer(self, class_id: str, trainer_id: str) -> WorkoutClass:
        clean_trainer_id = self._validate_non_empty_string(trainer_id, "Trainer id")

        # Lock order everywhere: member, then trainer, then class
        trainer = self._find_trainer(clean_trainer_id, for_update=True)
        workout_class = self._find_class(class_id, for_update=True)

        workout_class.assign_trainer(trainer.id)
        self.repo.save_class(workout_class)
        return workout_class

    @transactional
    def remove_trainer(self, class_id: str) -> WorkoutClass:
        workout_class = self._find_class(class_id, for_update=True)

        workout_class.remove_trainer()  # raises RuleViolationError if there is none
        self.repo.save_class(workout_class)
        return workout_class