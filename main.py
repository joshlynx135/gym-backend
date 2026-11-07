from typing import Optional

from fastapi import Depends, FastAPI, Query, status

from api.error_handlers import register_error_handlers
from api.schemas import BookingCreate, ClassPayload, MemberPayload
from repositories.gym_repository import GymRepository
from services.gym_service import GymService

app = FastAPI(title="Gym API")
register_error_handlers(app)

repo = GymRepository()


def get_service() -> GymService:
    return GymService(repo)


# Members 
@app.post("/api/members", status_code=status.HTTP_201_CREATED)
def create_member(data: MemberPayload, service: GymService = Depends(get_service)):
    return service.create_member(data.name, data.type).to_dict()


@app.get("/api/members")
def list_members(type: Optional[str] = None, service: GymService = Depends(get_service)):
    # Optional filter: GET /api/members?type=premium
    return [m.to_dict() for m in service.list_members(member_type=type)]


@app.get("/api/members/{member_id}")
def get_member(member_id: str, service: GymService = Depends(get_service)):
    return service.get_member(member_id).to_dict()


@app.put("/api/members/{member_id}")
def replace_member(member_id: str, data: MemberPayload, service: GymService = Depends(get_service)):
    return service.update_member(member_id, new_name=data.name, new_type=data.type).to_dict()


@app.delete("/api/members/{member_id}")
def delete_member(member_id: str, service: GymService = Depends(get_service)):
    service.delete_member(member_id)
    return {"message": "Member deleted."}


# Classes 
@app.post("/api/classes", status_code=status.HTTP_201_CREATED)
def create_class(data: ClassPayload, service: GymService = Depends(get_service)):
    return service.create_class(data.name, data.max_capacity).to_dict()


@app.get("/api/classes")
def list_classes(min_capacity: Optional[int] = Query(None), service: GymService = Depends(get_service)):
    # Optional filter: GET /api/classes?min_capacity=10
    return [c.to_dict() for c in service.list_classes(min_capacity=min_capacity)]


@app.get("/api/classes/{class_id}")
def get_class(class_id: str, service: GymService = Depends(get_service)):
    return service.get_class(class_id).to_dict()


@app.put("/api/classes/{class_id}")
def replace_class(class_id: str, data: ClassPayload, service: GymService = Depends(get_service)):
    return service.update_class(class_id, new_name=data.name, new_capacity=data.max_capacity).to_dict()


@app.delete("/api/classes/{class_id}")
def delete_class(class_id: str, service: GymService = Depends(get_service)):
    service.delete_class(class_id)
    return {"message": "Class deleted."}


# Bookings (nested under the class)
@app.post("/api/classes/{class_id}/bookings", status_code=status.HTTP_201_CREATED)
def book_class(class_id: str, data: BookingCreate, service: GymService = Depends(get_service)):
    booked = service.book_class(data.member_id, class_id)
    return {
        "message": f"Member {data.member_id} successfully booked for class {class_id}.",
        "class": booked.to_dict(),
    }


@app.delete("/api/classes/{class_id}/bookings/{member_id}")
def cancel_booking(class_id: str, member_id: str, service: GymService = Depends(get_service)):
    updated = service.cancel_booking(member_id, class_id)
    return {"message": "Booking cancelled.", "class": updated.to_dict()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8080)