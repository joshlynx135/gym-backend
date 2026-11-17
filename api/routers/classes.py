from typing import Optional

from fastapi import APIRouter, status

from api.dependencies import ServiceDep
from api.schemas import BookingCreate, ClassCreate, ClassUpdate
router = APIRouter(prefix="/api/classes", tags=["Classes"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_class(data: ClassCreate, service: ServiceDep):
    return service.create_class(data.name, data.max_capacity).to_dict()

@router.get("")
def list_classes(service: ServiceDep, min_capacity: Optional[int] = None):
    # Optional filter: GET /api/classes?min_capacity=10
    return [c.to_dict() for c in service.list_classes(min_capacity=min_capacity)]


@router.get("/{class_id}")
def get_class(class_id: str, service: ServiceDep):
    return service.get_class(class_id).to_dict()


@router.put("/{class_id}")
def update_class(class_id: str, data: ClassUpdate, service: ServiceDep):
    return service.update_class(class_id, new_name=data.name, new_capacity=data.max_capacity).to_dict()

@router.delete("/{class_id}")
def delete_class(class_id: str, service: ServiceDep):
    service.delete_class(class_id)
    return {"message": "Class deleted."}


# Bookings live under the class they belong to
@router.post("/{class_id}/bookings", status_code=status.HTTP_201_CREATED)
def book_class(class_id: str, data: BookingCreate, service: ServiceDep):
    booked = service.book_class(data.member_id, class_id)
    return {
        "message": f"Member {data.member_id} successfully booked for class {class_id}.",
        "class": booked.to_dict(),
    }


@router.delete("/{class_id}/bookings/{member_id}")
def cancel_booking(class_id: str, member_id: str, service: ServiceDep):
    updated = service.cancel_booking(member_id, class_id)
    return {"message": "Booking cancelled.", "class": updated.to_dict()}