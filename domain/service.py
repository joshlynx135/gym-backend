import uuid
import threading
from domain.models import WorkoutClass, BasicMember, PremiumMember
from domain.exceptions import NotFoundError, RuleViolationError

class GymService:
    def __init__(self):
        self.classes = {}
        self.members = {}
        self._lock = threading.RLock()

    @staticmethod
    def _validate_non_empty_string(value, field_name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise RuleViolationError(f"{field_name} must be a non-empty string.")
        return value.strip()

    @staticmethod
    def _validate_capacity(value) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise RuleViolationError("Capacity must be a positive integer greater than 0.")
        return value

    #CRUD for members
    
    def create_member(self, name: str, member_type: str):
        with self._lock:
            clean_name = self._validate_non_empty_string(name, "Member name")
            if not isinstance(member_type, str):
                raise RuleViolationError("Type must be either 'BASIC' or 'PREMIUM'.")

            member_id = f"m-{uuid.uuid4().hex[:4]}"
            target_type = member_type.strip().upper()
            if target_type == "BASIC":
                member = BasicMember(member_id, clean_name)
            elif target_type == "PREMIUM":
                member = PremiumMember(member_id, clean_name)
            else:
                raise RuleViolationError("Type must be either 'BASIC' or 'PREMIUM'.")

            self.members[member_id] = member
            return member

    def get_member(self, member_id: str):
        with self._lock:
            if member_id not in self.members:
                raise NotFoundError(f"Member with ID {member_id} not found.")
            return self.members[member_id]

    def list_members(self, member_type: str = None):
        with self._lock:
            all_members = list(self.members.values())
            if member_type is not None:
                target = member_type.strip().upper()
                if target == "BASIC":
                    all_members = [m for m in all_members if isinstance(m, BasicMember)]
                elif target == "PREMIUM":
                    all_members = [m for m in all_members if isinstance(m, PremiumMember)]
                else:
                    raise RuleViolationError("Filter type must be 'BASIC' or 'PREMIUM'.")
            return all_members

    def update_member(self, member_id: str, new_name: str = None, new_type: str = None):
        with self._lock:
            member = self.get_member(member_id)
            if new_name is None and new_type is None:
                raise RuleViolationError("At least one field ('name' or 'type') must be provided for update.")

            if new_name is not None:
                member.name = self._validate_non_empty_string(new_name, "Member name")

            if new_type is not None:
                if not isinstance(new_type, str):
                    raise RuleViolationError("Type must be either 'BASIC' or 'PREMIUM'.")
                target_type = new_type.strip().upper()
                current_type = "BASIC" if isinstance(member, BasicMember) else "PREMIUM"

                if target_type != current_type:
                    if target_type == "PREMIUM":
                        new_member = PremiumMember(member_id, member.name)
                    elif target_type == "BASIC":
                        new_member = BasicMember(member_id, member.name)
                    else:
                        raise RuleViolationError("Type must be either 'BASIC' or 'PREMIUM'.")

                    current_bookings = sum(
                        1 for cls in self.classes.values() if member_id in cls.enrolled_members_ids
                    )
                    if current_bookings > new_member.get_max_bookings():
                        raise RuleViolationError(
                            f"Cannot change type to {target_type}: member has {current_bookings} active bookings, "
                            f"which exceeds the new limit of {new_member.get_max_bookings()}."
                        )

                    self.members[member_id] = new_member
                    member = new_member
            return member

    def delete_member(self, member_id: str):
        with self._lock:
            self.get_member(member_id)
            for workout_class in self.classes.values():
                if member_id in workout_class.enrolled_members_ids:
                    workout_class.enrolled_members_ids.remove(member_id)
            del self.members[member_id]

    # CRUD for workout classes
    def create_class(self, name: str, max_capacity: int):
        with self._lock:
            clean_name = self._validate_non_empty_string(name, "Class name")
            clean_capacity = self._validate_capacity(max_capacity)
            class_id = f"c-{uuid.uuid4().hex[:4]}"
            workout_class = WorkoutClass(class_id, clean_name, clean_capacity)
            self.classes[class_id] = workout_class
            return workout_class

    def get_class(self, class_id: str):
        with self._lock:
            if class_id not in self.classes:
                raise NotFoundError(f"Class with ID {class_id} not found.")
            return self.classes[class_id]

    def list_classes(self, min_capacity: int = None):
        with self._lock:
            all_classes = list(self.classes.values())
            if min_capacity is not None:
                all_classes = [cls for cls in all_classes if cls.max_capacity >= min_capacity]
            return all_classes

    def update_class(self, class_id: str, new_name: str = None, new_capacity: int = None):
        with self._lock:
            workout_class = self.get_class(class_id)
            if new_name is None and new_capacity is None:
                raise RuleViolationError("At least one field ('name' or 'max_capacity') must be provided for update.")

            if new_name is not None:
                workout_class.name = self._validate_non_empty_string(new_name, "Class name")

            if new_capacity is not None:
                clean_capacity = self._validate_capacity(new_capacity)
                if clean_capacity < len(workout_class.enrolled_members_ids):
                    raise RuleViolationError("Cannot lower capacity below current enrollments.")
                workout_class.max_capacity = clean_capacity
            return workout_class

    def delete_class(self, class_id: str):
        with self._lock:
            self.get_class(class_id)
            del self.classes[class_id]
    #DOMAIN operations

    def book_class(self, member_id: str, class_id: str):
        with self._lock:
            if not isinstance(member_id, str) or not isinstance(class_id, str):
                raise RuleViolationError("Both 'member_id' and 'class_id' must be valid strings.")

            member = self.get_member(member_id)
            workout_class = self.get_class(class_id)

            if len(workout_class.enrolled_members_ids) >= workout_class.max_capacity:
                raise RuleViolationError(f"Class {workout_class.name} is full.")

            if member_id in workout_class.enrolled_members_ids:
                raise RuleViolationError(f"Member {member.name} is already booked for class {workout_class.name}.")

            current_bookings = sum(1 for cls in self.classes.values() if member_id in cls.enrolled_members_ids)
            if current_bookings >= member.get_max_bookings():
                raise RuleViolationError(f"Member {member.name} has reached their booking limit.")

            workout_class.enrolled_members_ids.append(member_id)
            return workout_class

    def cancel_booking(self, member_id: str, class_id: str):
        with self._lock:
            if not isinstance(member_id, str) or not isinstance(class_id, str):
                raise RuleViolationError("Both 'member_id' and 'class_id' must be valid strings.")

            self.get_member(member_id)
            workout_class = self.get_class(class_id)

            if member_id not in workout_class.enrolled_members_ids:
                raise RuleViolationError("Member is not enrolled in this class.")

            workout_class.enrolled_members_ids.remove(member_id)
            return workout_class