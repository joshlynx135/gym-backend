from dataclasses import dataclass
from typing import Optional
from abc import ABC, abstractmethod
from collections.abc import Iterable
from domain.exceptions import RuleViolationError


class WorkoutClass:
    
    def __init__(
        self,
        class_id: str,
        name: str,
        max_capacity: int,
        enrolled_member_ids: Iterable[str] = (),
        trainer_id: Optional[str] = None,
    ) -> None:
        self.id = class_id
        self.name = name
        self.max_capacity = max_capacity
        # list(...) copies the input, so this object never shares a collection with its caller
        self._enrolled_member_ids: list[str] = list(enrolled_member_ids)
        # Id of the trainer who teaches this class, or None when nobody is assigned
        self.trainer_id = trainer_id

    @property
    def enrolled_members_ids(self) -> tuple[str, ...]:
        # A tuple is immutable
        return tuple(self._enrolled_member_ids)

    @property
    def enrolled_count(self) -> int:
        return len(self._enrolled_member_ids)

    def is_enrolled(self, member_id: str) -> bool:
        return member_id in self._enrolled_member_ids

    def is_full(self) -> bool:
        return self.enrolled_count >= self.max_capacity

    def ensure_can_enroll(self, member_id: str) -> None:
        if self.is_enrolled(member_id):
            raise RuleViolationError(f"Member {member_id} is already booked for class {self.name}.")
        if self.is_full():
            raise RuleViolationError(f"Class {self.name} is full.")

    def enroll(self, member_id: str) -> None:
        self.ensure_can_enroll(member_id)  # the class guards itself even if caller forgets to
        self._enrolled_member_ids.append(member_id)

    def unenroll(self, member_id: str) -> None:
        if not self.is_enrolled(member_id):
            raise RuleViolationError("Member is not enrolled in this class.")
        self._enrolled_member_ids.remove(member_id)

    def resize(self, new_capacity: int) -> None:
        #Change capacity Raises BEFORE changing anything if it would evict people.
        if new_capacity < self.enrolled_count:
            raise RuleViolationError("Cannot lower capacity below current enrollments.")
        self.max_capacity = new_capacity

    def assign_trainer(self, trainer_id: str) -> None:
        """Set the trainer, replacing any previous one."""
        self.trainer_id = trainer_id

    def remove_trainer(self) -> None:
        if self.trainer_id is None:
            raise RuleViolationError("Class has no trainer assigned.")
        self.trainer_id = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "max_capacity": self.max_capacity,
            "enrolled": self.enrolled_count,
            "trainer_id": self.trainer_id,
        }

class Trainer:
    """A person who teaches classes."""
    def __init__(self, trainer_id: str, name:str) -> None:
        self.id = trainer_id
        self.name = name

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name}
    
class Member(ABC):
    type_name: str

    def __init__(self, member_id: str, name: str) -> None:
        self.id = member_id
        self.name = name

    @abstractmethod
    def get_max_bookings(self) -> int:
        """How many classes this member type may hold at once."""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type_name,  # "BASIC" / "PREMIUM", not "BasicMember"
            "max_bookings": self.get_max_bookings(),
        }


class BasicMember(Member):
    type_name = "BASIC"

    def get_max_bookings(self) -> int:
        return 1  # Basic members can hold only 1 booking at a time


class PremiumMember(Member):
    type_name = "PREMIUM"

    def get_max_bookings(self) -> int:
        return 3  # Premium members can hold up to 3 bookings at a time

def build_member(member_id: str, name: str, member_type: str) -> Member:
    """Create the right Member subclass for a stored type label."""
    if member_type == BasicMember.type_name:
        return BasicMember(member_id, name)
    if member_type == PremiumMember.type_name:
        return PremiumMember(member_id, name)
    raise ValueError(f"Unknown member type: {member_type}")

@dataclass(frozen=True)
class ClassDetails:
    """A read-only view of a class together with the objects it relates to."""

    workout_class: WorkoutClass
    trainer: Optional[Trainer]
    members: tuple[Member, ...]

    def to_dict(self) -> dict:
        data = self.workout_class.to_dict()
        data["trainer"] = self.trainer.to_dict() if self.trainer is not None else None
        data["members"] = [member.to_dict() for member in self.members]
        return data