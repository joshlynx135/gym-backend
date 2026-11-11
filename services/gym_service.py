import copy
from typing import Optional

from domain.exceptions import NotFoundError, RuleViolationError, ValidationError
from domain.models import BasicMember, Member, PremiumMember, WorkoutClass
from repositories.gym_repository import GymRepository


class GymService:
    """Business rules for members, classes and bookings.

    Thread-safety contract:
      * every public method runs under repo.lock;
      * public methods NEVER return the objects stored in the repository, only
        deep copies made while the lock is still held. Callers can therefore read
        (and even modify) what they receive without affecting stored data or racing
        with other requests.
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

    @staticmethod
    def _build_member(member_id: str, name: str, member_type: str) -> Member:
        if member_type == "PREMIUM":
            return PremiumMember(member_id, name)
        return BasicMember(member_id, name)

    # ---- Internal helpers: work on the LIVE stored objects ----
    # Callers must hold repo.lock, and the result must never leave this class.
    def _find_member(self, member_id: str) -> Member:
        member = self.repo.get_member(member_id)
        if member is None:
            raise NotFoundError(f"Member with ID {member_id} not found.")
        return member

    def _find_class(self, class_id: str) -> WorkoutClass:
        workout_class = self.repo.get_class(class_id)
        if workout_class is None:
            raise NotFoundError(f"Class with ID {class_id} not found.")
        return workout_class

    def _count_bookings(self, member_id: str) -> int:
        return sum(1 for cls in self.repo.list_classes() if cls.is_enrolled(member_id))

    # ---- Members ----
    def create_member(self, name: str, member_type: str) -> Member:
        with self.repo.lock:
            clean_name = self._validate_non_empty_string(name, "Member name")
            target_type = self._validate_member_type(member_type)

            member = self._build_member(self.repo.next_member_id(), clean_name, target_type)
            self.repo.save_member(member)
            return copy.deepcopy(member)  # the copy is made BEFORE the lock is released

    def get_member(self, member_id: str) -> Member:
        with self.repo.lock:
            return copy.deepcopy(self._find_member(member_id))

    def list_members(self, member_type: Optional[str] = None) -> list[Member]:
        with self.repo.lock:
            members = self.repo.list_members()
            if member_type is not None:
                target = self._validate_member_type(member_type, "Filter type")
                members = [m for m in members if m.type_name == target]
            return [copy.deepcopy(m) for m in members]

    def update_member(
        self, member_id: str, new_name: Optional[str] = None, new_type: Optional[str] = None
    ) -> Member:
        with self.repo.lock:
            member = self._find_member(member_id)  # LIVE object: we modify it below
            if new_name is None and new_type is None:
                raise ValidationError("At least one field ('name' or 'type') must be provided for update.")

            # Phase 1: validate everything, mutate nothing.
            clean_name = (
                self._validate_non_empty_string(new_name, "Member name")
                if new_name is not None else member.name
            )

            replacement = None
            if new_type is not None:
                target_type = self._validate_member_type(new_type)
                if target_type != member.type_name:
                    replacement = self._build_member(member_id, clean_name, target_type)
                    current_bookings = self._count_bookings(member_id)
                    if current_bookings > replacement.get_max_bookings():
                        raise RuleViolationError(
                            f"Cannot change type to {target_type}: member has {current_bookings} active bookings, "
                            f"which exceeds the new limit of {replacement.get_max_bookings()}."
                        )

            # Phase 2: apply the change
            if replacement is not None:
                self.repo.save_member(replacement)
                return copy.deepcopy(replacement)
            member.name = clean_name
            return copy.deepcopy(member)

    def delete_member(self, member_id: str) -> None:
        with self.repo.lock:
            self._find_member(member_id)  # raises NotFoundError if missing
            # Cascade: remove this member from every class they booked
            for workout_class in self.repo.list_classes():
                if workout_class.is_enrolled(member_id):
                    workout_class.unenroll(member_id)
            self.repo.delete_member(member_id)

    # ---- Workout classes ----
    def create_class(self, name: str, max_capacity: int) -> WorkoutClass:
        with self.repo.lock:
            clean_name = self._validate_non_empty_string(name, "Class name")
            clean_capacity = self._validate_capacity(max_capacity)
            workout_class = WorkoutClass(self.repo.next_class_id(), clean_name, clean_capacity)
            self.repo.save_class(workout_class)
            return copy.deepcopy(workout_class)

    def get_class(self, class_id: str) -> WorkoutClass:
        with self.repo.lock:
            return copy.deepcopy(self._find_class(class_id))

    def list_classes(self, min_capacity: Optional[int] = None) -> list[WorkoutClass]:
        with self.repo.lock:
            classes = self.repo.list_classes()
            if min_capacity is not None:
                if isinstance(min_capacity, bool) or not isinstance(min_capacity, int):
                    raise ValidationError("min_capacity must be an integer.")
                classes = [cls for cls in classes if cls.max_capacity >= min_capacity]
            return [copy.deepcopy(cls) for cls in classes]

    def update_class(
        self, class_id: str, new_name: Optional[str] = None, new_capacity: Optional[int] = None
    ) -> WorkoutClass:
        with self.repo.lock:
            workout_class = self._find_class(class_id)  # LIVE object: we modify it below
            if new_name is None and new_capacity is None:
                raise ValidationError("At least one field ('name' or 'max_capacity') must be provided for update.")

            # Validate the name first: nothing has been changed yet
            clean_name = (
                self._validate_non_empty_string(new_name, "Class name")
                if new_name is not None else workout_class.name
            )
            # resize() raises BEFORE changing anything if the new capacity is too small
            if new_capacity is not None:
                workout_class.resize(self._validate_capacity(new_capacity))

            workout_class.name = clean_name  # cannot fail, so it goes last
            return copy.deepcopy(workout_class)

    def delete_class(self, class_id: str) -> None:
        with self.repo.lock:
            self._find_class(class_id)  # raises NotFoundError if missing
            self.repo.delete_class(class_id)

    # ---- Domain operations ----
    def book_class(self, member_id: str, class_id: str) -> WorkoutClass:
        with self.repo.lock:
            self._validate_id_pair(member_id, class_id)

            member = self._find_member(member_id)
            workout_class = self._find_class(class_id)

            # The class checks "already booked" and "full"; the service checks the
            # member's limit, because that needs a view across ALL classes
            workout_class.ensure_can_enroll(member_id)
            if self._count_bookings(member_id) >= member.get_max_bookings():
                raise RuleViolationError(f"Member {member.name} has reached their booking limit.")

            workout_class.enroll(member_id)
            return copy.deepcopy(workout_class)

    def cancel_booking(self, member_id: str, class_id: str) -> WorkoutClass:
        with self.repo.lock:
            self._validate_id_pair(member_id, class_id)

            self._find_member(member_id)
            workout_class = self._find_class(class_id)

            workout_class.unenroll(member_id)  # raises RuleViolationError if not enrolled
            return copy.deepcopy(workout_class)