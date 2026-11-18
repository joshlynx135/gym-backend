import functools
from typing import Optional

from domain.exceptions import NotFoundError, RuleViolationError, ValidationError
from domain.models import Member, WorkoutClass, build_member
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

    # ---- Workout classes ----
    @transactional
    def create_class(self, name: str, max_capacity: int) -> WorkoutClass:
        clean_name = self._validate_non_empty_string(name, "Class name")
        clean_capacity = self._validate_capacity(max_capacity)

        workout_class = WorkoutClass(self.repo.next_class_id(), clean_name, clean_capacity)
        self.repo.save_class(workout_class)
        return workout_class

    @transactional
    def get_class(self, class_id: str) -> WorkoutClass:
        return self._find_class(class_id)

    @transactional
    def list_classes(self, min_capacity: Optional[int] = None) -> list[WorkoutClass]:
        classes = self.repo.list_classes()
        if min_capacity is not None:
            if isinstance(min_capacity, bool) or not isinstance(min_capacity, int):
                raise ValidationError("min_capacity must be an integer.")
            classes = [cls for cls in classes if cls.max_capacity >= min_capacity]
        return classes

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