import threading
import uuid
from typing import Optional

from domain.models import Member, WorkoutClass
 

class GymRepository:
    
    
    def __init__(self) -> None:
        self._members: dict[str, Member] = {}
        self._classes: dict[str, WorkoutClass] = {}
        self.lock = threading.RLock()
        
    
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
    
    # Members
    def save_member(self, member: Member) -> None:
        self._members[member.id] = member

    def get_member(self, member_id: str) -> Optional[Member]:
        return self._members.get(member_id)

    def list_members(self) -> list[Member]:
        return list(self._members.values())

    def delete_member(self, member_id: str) -> None:
        self._members.pop(member_id, None)
        
    # Classes
    
    def save_class(self, workout_class: WorkoutClass) -> None:
        self._classes[workout_class.id] = workout_class

    def get_class(self, class_id: str) -> Optional[WorkoutClass]:
        return self._classes.get(class_id)

    def list_classes(self) -> list[WorkoutClass]:
        return list(self._classes.values())

    def delete_class(self, class_id: str) -> None:
        self._classes.pop(class_id, None)