import uuid 
from domain.models import WorkoutClass, BasicMember, PremiumMember
from domain.exceptions import NotFoundError, RuleViolationError

class GymService:
    def __init__(self):
        self.classes = {}  
        self.members = {}
    
    #CRUD for members
    
    def create_member(self, name: str, member_type: str):
        member_id = f"m-{uuid.uuid4().hex[:4]}"
        if member_type.upper() == "BASIC":
            member = BasicMember(member_id, name)
        elif member_type.upper() == "PREMIUM":
            member = PremiumMember(member_id, name)
        else:
            raise RuleViolationError("Type must be either 'BASIC' or 'PREMIUM'.")

        self.members[member_id] = member
        return member
    
    def get_member(self, member_id: str):
        if member_id not in self.members:
            raise NotFoundError(f"Member with ID {member_id} not found.")
        return self.members[member_id]
    
    def list_members(self):
        return list(self.members.values())
    
    def update_member(self, member_id: str, new_name: str):
        member = self.get_member(member_id)
        if new_name:
            member.name = new_name
        return member

    def delete_member(self, member_id: str):
        self.get_member(member_id)  # This should raise NotFoundError if the member doesn't exist I hope
        del self.members[member_id]
    #CRUD for workout classes
    
    def create_class(self, name: str, max_capacity: int):
        class_id = f"c-{uuid.uuid4().hex[:4]}"
        workout_class = WorkoutClass(class_id, name, max_capacity)
        self.classes[class_id] = workout_class
        return workout_class
    
    def get_class(self, class_id: str):
        if class_id not in self.classes:
            raise NotFoundError(f"Class with ID {class_id} not found.")
        return self.classes[class_id]
    
    def list_classes(self, min_capacity: int = None):
        all_classes = list(self.classes.values())
        if min_capacity is not None:
            all_classes = [cls for cls in all_classes if cls.max_capacity >= min_capacity]
        return all_classes
    
    def update_class(self, class_id: str, new_name: str = None, new_capacity: int = None):
        workout_class = self.get_class(class_id)
        if new_name:
            workout_class.name = new_name
        if new_capacity:
            if new_capacity < len(workout_class.enrolled_members_ids):
                raise RuleViolationError("Cannot lower capacity below current enrollments.")
            workout_class.max_capacity = new_capacity
        return workout_class
    
    def delete_class(self, class_id: str):
        self.get_class(class_id)  
        del self.classes[class_id]
    #DOMAIN opertions
    
    def book_class(self, member_id: str, class_id: str):
        member = self.get_member(member_id)
        workout_class = self.get_class(class_id)

        if len(workout_class.enrolled_members_ids) >= workout_class.max_capacity:
            raise RuleViolationError(f"Class {workout_class.name} is full.")
        
        if member_id in workout_class.enrolled_members_ids:
            raise RuleViolationError(f"Member {member.name} is already booked for class {workout_class.name}.")
        
        # Check if the member has reached their booking limit
        current_bookings = sum(1 for cls in self.classes.values() if member_id in cls.enrolled_members_ids)
        if current_bookings >= member.get_max_bookings():
            raise RuleViolationError(f"Member {member.name} has reached their booking limit.")

        workout_class.enrolled_members_ids.append(member_id)
        return workout_class
    