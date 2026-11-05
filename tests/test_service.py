import pytest
from domain.repository import GymRepository
from domain.service import GymService
from domain.exceptions import RuleViolationError, NotFoundError, ValidationError

@pytest.fixture
def service():
    repo = GymRepository()
    return GymService(repo)


def test_create_and_get_member(service: GymService):
    member = service.create_member("Vincent", "BASIC")
    
    assert member.name == "Vincent"
    assert member.get_max_bookings() == 1
    
    fetched = service.get_member(member.id)
    assert fetched.id == member.id

def test_successful_booking(service: GymService):
    member = service.create_member("Vera", "PREMIUM")
    workout = service.create_class("Morning Yoga", 5)
    
    service.book_class(member.id, workout.id)
    
    updated_workout = service.get_class(workout.id)
    assert member.id in updated_workout.enrolled_members_ids



def test_booking_limit_violation(service: GymService):
    # Basic members can only book 1 class
    member = service.create_member("John", "BASIC")
    workout1 = service.create_class("Yoga", 5)
    workout2 = service.create_class("Boxing", 5)
    
    # First booking should succeed
    service.book_class(member.id, workout1.id)
    
    # Second booking should raise a RuleViolationError
    with pytest.raises(RuleViolationError) as exc_info:
        service.book_class(member.id, workout2.id)
    
    assert "booking limit" in str(exc_info.value)

def test_class_capacity_violation(service: GymService):
    # Class with capacity of 1
    workout = service.create_class("Exclusive Yoga", 1)
    member1 = service.create_member("Vincent", "PREMIUM")
    member2 = service.create_member("Vera", "PREMIUM")
    
    service.book_class(member1.id, workout.id)
    
    # Second booking should fail because capacity is 1
    with pytest.raises(RuleViolationError) as exc_info:
        service.book_class(member2.id, workout.id)
        
    assert "is full" in str(exc_info.value)



def test_cascading_delete_removes_bookings(service: GymService):
    member = service.create_member("Vincent", "BASIC")
    workout = service.create_class("Yoga", 5)
    
    service.book_class(member.id, workout.id)
    
    # Delete the member
    service.delete_member(member.id)
    
    updated_workout = service.get_class(workout.id)
    assert member.id not in updated_workout.enrolled_members_ids

def test_downgrade_with_active_bookings_blocked(service: GymService):
    member = service.create_member("Vera", "PREMIUM")
    workout1 = service.create_class("Yoga", 5)
    workout2 = service.create_class("Boxing", 5)
    
    service.book_class(member.id, workout1.id)
    service.book_class(member.id, workout2.id)
    
    with pytest.raises(RuleViolationError) as exc_info:
        service.update_member(member.id, new_type="BASIC")
        
    assert "exceeds the new limit" in str(exc_info.value)