from abc import ABC, abstractmethod

class WorkoutClass:
    def __init__(self, class_id: str, name: str, max_capacity: int):
        self.id = class_id
        self.name = name
        self.max_capacity = max_capacity
        self.enrolled_members_ids = [] #list of members who booked this class
        
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "max_capacity": self.max_capacity,
            "enrolled": len(self.enrolled_members_ids)
        }
class Member(ABC):
    def __init__(self, member_id: str, name: str):
        self.id = member_id
        self.name = name

    @abstractmethod
    def get_max_bookings(self) -> int:
        pass

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "type": self.__class__.__name__,
            "max_bookings": self.get_max_bookings()
        }

class BasicMember(Member):
    def get_max_bookings(self) -> int:
        return 1 #Basic members can book only 1 class at a time
class PremiumMember(Member):
    def get_max_bookings(self) -> int:
        return 3 #Premium members can book up to 3 classes at a time