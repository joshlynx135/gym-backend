import copy
import uuid
from typing import Optional
from contextlib import AbstractContextManager, nullcontext

from domain.models import Member, Trainer, WorkoutClass


class InMemoryGymRepository:
    """Dictionary-based repository used by the unit tests.

    It follows the same contract as the PostgreSQL repository: callers always receive
    copies, and a change becomes stored only when save_* is called.
    """

    def __init__(self) -> None:
        self._members: dict[str, Member] = {}
        self._classes: dict[str, WorkoutClass] = {}
        self._trainers: dict[str, Trainer] = {}

    #ID generation 
    @staticmethod
    def _new_id(prefix: str, existing: dict) -> str:
        while True:
            candidate = f"{prefix}-{uuid.uuid4().hex[:8]}"
            if candidate not in existing:
                return candidate

    def next_member_id(self) -> str:
        return self._new_id("m", self._members)

    def next_class_id(self) -> str:
        return self._new_id("c", self._classes)

    #Members 
    def save_member(self, member: Member) -> None:
        self._members[member.id] = copy.deepcopy(member)

    def get_member(self, member_id: str, *, for_update: bool = False) -> Optional[Member]:
        member = self._members.get(member_id)
        return copy.deepcopy(member) if member is not None else None

    def list_members(self) -> list[Member]:
        return [copy.deepcopy(member) for member in self._members.values()]

    def delete_member(self, member_id: str) -> None:
        self._members.pop(member_id, None)
        # Imitates ON DELETE CASCADE of the SQL schema: remove the member's bookings
        for workout_class in self._classes.values():
            if workout_class.is_enrolled(member_id):
                workout_class.unenroll(member_id)

    #Classes 
    def save_class(self, workout_class: WorkoutClass) -> None:
        self._classes[workout_class.id] = copy.deepcopy(workout_class)

    def get_class(self, class_id: str, *, for_update: bool = False) -> Optional[WorkoutClass]:
        workout_class = self._classes.get(class_id)
        return copy.deepcopy(workout_class) if workout_class is not None else None

    def list_classes(self) -> list[WorkoutClass]:
        return [copy.deepcopy(workout_class) for workout_class in self._classes.values()]

    def delete_class(self, class_id: str) -> None:
        # The roster lives inside the class object, so its bookings disappear with it
        self._classes.pop(class_id, None)

    # Bookings
    def count_bookings_of_member(self, member_id: str) -> int:
        return sum(1 for workout_class in self._classes.values() if workout_class.is_enrolled(member_id))

    # Trainers 
    def next_trainer_id(self) -> str:
        return self._new_id("t", self._trainers)

    def save_trainer(self, trainer: Trainer) -> None:
        self._trainers[trainer.id] = copy.deepcopy(trainer)

    def get_trainer(self, trainer_id: str, *, for_update: bool = False) -> Optional[Trainer]:
        trainer = self._trainers.get(trainer_id)
        return copy.deepcopy(trainer) if trainer is not None else None

    def list_trainers(self) -> list[Trainer]:
        return [copy.deepcopy(trainer) for trainer in self._trainers.values()]

    def delete_trainer(self, trainer_id: str) -> None:
        self._trainers.pop(trainer_id, None)

    def count_classes_of_trainer(self, trainer_id: str) -> int:
        return sum(1 for workout_class in self._classes.values() if workout_class.trainer_id == trainer_id)
    
    # Transations
    def transaction(self) -> AbstractContextManager[None]:
        #The in-memory store has nothing to commit or roll back
        return nullcontext()