from typing import Optional

from domain.exceptions import NotFoundError, RuleViolationError, ValidationError
from domain.models import BasicMember, Member, PremiumMember, WorkoutClass
from repositories.gym_repository import GymRepository


class GymService:
    def __init__(self, repo: GymRepository) -> None:
        self.repo = repo

    # Validation helpers (malformed input -> ValidationError -> HTTP 400)
    @staticmethod
    def _validate_non_empty_string(value, field_name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValidationError(f"{field_name} must be a non-empty string.")
        return value.strip()

    @staticmethod
    def _validate_capacity(value) -> int:
        # bool is a subclass of int in Python, so True would sneak through without this check
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

    # helpers
    def _count_bookings(self, member_id: str) -> int:
        return sum(1 for cls in self.repo.list_classes() if member_id in cls.enrolled_members_ids)

    # Members
    def create_member(self, name: str, member_type: str) -> Member:
        with self.repo.lock:  # one operation at a time
            clean_name = self._validate_non_empty_string(name, "Member name")
            target_type = self._validate_member_type(member_type)

            member = self._build_member(self.repo.next_member_id(), clean_name, target_type)
            self.repo.save_member(member)
            return member

    def get_member(self, member_id: str) -> Member:
        with self.repo.lock:
            member = self.repo.get_member(member_id)
            if member is None:
                raise NotFoundError(f"Member with ID {member_id} not found.")
            return member

    def list_members(self, member_type: Optional[str] = None) -> list[Member]:
        with self.repo.lock:
            all_members = self.repo.list_members()
            if member_type is not None:
                target = self._validate_member_type(member_type, "Filter type")
                expected = PremiumMember if target == "PREMIUM" else BasicMember
                all_members = [m for m in all_members if isinstance(m, expected)]
            return all_members

    def update_member(
        self, member_id: str, new_name: Optional[str] = None, new_type: Optional[str] = None
    ) -> Member:
        with self.repo.lock:
            member = self.get_member(member_id)
            if new_name is None and new_type is None:
                raise ValidationError("At least one field ('name' or 'type') must be provided for update.")

            # If anything fails, the stored data is left exactly as it was.
            clean_name = (
                self._validate_non_empty_string(new_name, "Member name")
                if new_name is not None else member.name
            )

            replacement = None
            if new_type is not None:
                target_type = self._validate_member_type(new_type)
                current_type = "BASIC" if isinstance(member, BasicMember) else "PREMIUM"
                if target_type != current_type:
                    replacement = self._build_member(member_id, clean_name, target_type)
                    current_bookings = self._count_bookings(member_id)
                    if current_bookings > replacement.get_max_bookings():
                        raise RuleViolationError(
                            f"Cannot change type to {target_type}: member has {current_bookings} active bookings, "
                            f"which exceeds the new limit of {replacement.get_max_bookings()}."
                        )

            # apply the change
            if replacement is not None:
                self.repo.save_member(replacement)
                return replacement
            member.name = clean_name
            return member

    def delete_member(self, member_id: str) -> None:
        with self.repo.lock:
            self.get_member(member_id)  # raises NotFoundError if missing
            for workout_class in self.repo.list_classes():
                if member_id in workout_class.enrolled_members_ids:
                    workout_class.enrolled_members_ids.remove(member_id)
            self.repo.delete_member(member_id)

    # Workout classes
    def create_class(self, name: str, max_capacity: int) -> WorkoutClass:
        with self.repo.lock:
            clean_name = self._validate_non_empty_string(name, "Class name")
            clean_capacity = self._validate_capacity(max_capacity)
            workout_class = WorkoutClass(self.repo.next_class_id(), clean_name, clean_capacity)
            self.repo.save_class(workout_class)
            return workout_class

    def get_class(self, class_id: str) -> WorkoutClass:
        with self.repo.lock:
            workout_class = self.repo.get_class(class_id)
            if workout_class is None:
                raise NotFoundError(f"Class with ID {class_id} not found.")
            return workout_class

    def list_classes(self, min_capacity: Optional[int] = None) -> list[WorkoutClass]:
        with self.repo.lock:
            all_classes = self.repo.list_classes()
            if min_capacity is not None:
                if isinstance(min_capacity, bool) or not isinstance(min_capacity, int):
                    raise ValidationError("min_capacity must be an integer.")
                all_classes = [cls for cls in all_classes if cls.max_capacity >= min_capacity]
            return all_classes

    def update_class(
        self, class_id: str, new_name: Optional[str] = None, new_capacity: Optional[int] = None
    ) -> WorkoutClass:
        with self.repo.lock:
            workout_class = self.get_class(class_id)
            if new_name is None and new_capacity is None:
                raise ValidationError("At least one field ('name' or 'max_capacity') must be provided for update.")

            # Validate everything first, mutate nothing
            clean_name = (
                self._validate_non_empty_string(new_name, "Class name")
                if new_name is not None else workout_class.name
            )
            clean_capacity = workout_class.max_capacity
            if new_capacity is not None:
                clean_capacity = self._validate_capacity(new_capacity)
                if clean_capacity < len(workout_class.enrolled_members_ids):
                    raise RuleViolationError("Cannot lower capacity below current enrollments.")

            # Apply
            workout_class.name = clean_name
            workout_class.max_capacity = clean_capacity
            return workout_class

    def delete_class(self, class_id: str) -> None:
        with self.repo.lock:
            self.get_class(class_id)  # raises NotFoundError if missing
            self.repo.delete_class(class_id)

    # Domain operations
    def book_class(self, member_id: str, class_id: str) -> WorkoutClass:
        with self.repo.lock:
            self._validate_id_pair(member_id, class_id)

            member = self.get_member(member_id)
            workout_class = self.get_class(class_id)

            if member_id in workout_class.enrolled_members_ids:
                raise RuleViolationError(f"Member {member.name} is already booked for class {workout_class.name}.")

            if len(workout_class.enrolled_members_ids) >= workout_class.max_capacity:
                raise RuleViolationError(f"Class {workout_class.name} is full.")

            if self._count_bookings(member_id) >= member.get_max_bookings():
                raise RuleViolationError(f"Member {member.name} has reached their booking limit.")

            workout_class.enrolled_members_ids.append(member_id)
            return workout_class

    def cancel_booking(self, member_id: str, class_id: str) -> WorkoutClass:
        with self.repo.lock:
            self._validate_id_pair(member_id, class_id)

            self.get_member(member_id)
            workout_class = self.get_class(class_id)

            if member_id not in workout_class.enrolled_members_ids:
                raise RuleViolationError("Member is not enrolled in this class.")

            workout_class.enrolled_members_ids.remove(member_id)
            return workout_class