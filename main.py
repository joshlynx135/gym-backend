from typing import Optional
from fastapi import FastAPI, Depends, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from repositories.gym_repository import GymRepository
from services.gym_service import GymService
from domain.exceptions import NotFoundError, RuleViolationError, ValidationError


app = FastAPI(title= "Gym API")

repo = GymRepository()

def get_service() -> GymService:
    return GymService(repo)

#PYDANTIC SCHEMAS

class MemberCreate(BaseModel):
    name: str = Field(..., min_length=1)
    type: str = Field(..., pattern="^(?i)(BASIC|PREMIUM)$") #case-sensitive

class MemberUpdate(BaseModel):
    name: str = Field(..., min_length=1)
    type: str = Field(..., pattern="^(?i)(BASIC|PREMIUM)$")

class ClassCreate(BaseModel):
    name: str = Field(..., min_length=1)
    max_capacity: int = Field(..., gt=0)
    
class ClassUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    max_capacity: Optional[int] = Field(None, gt=0)

class BookingRequest(BaseModel):
    member_id: str
    class_id: str

#GLOBAL ERROR HANDLERS

@app.exception_handler(NotFoundError)
async def not_found_handler(request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"error": str(exc)})

@app.exception_handler(RuleViolationError)
async def rule_violation_handler(request, exc: RuleViolationError):
    return JSONResponse(status_code=409, content={"error": str(exc)})

@app.exception_handler(ValidationError)
async def custom_validation_handler(request, exc: ValidationError):
    return JSONResponse(status_code=400, content={"error": str(exc)})

#ROUTES
@app.post("/api/members", status_code=status.HTTP_201_CREATED)
def create_member(data: MemberCreate, service: GymService = Depends(get_service)):
    member = service.create_member(data.name, data.type)
    return member.to_dict()

@app.get("/api/members")
def list_members(type: Optional[str] = None, service: GymService = Depends(get_service)):
    members = service.list_members(member_type=type)
    return [m.to_dict() for m in members]

@app.get("/api/members/{member_id}")
def get_member(member_id: str, service: GymService = Depends(get_service)):
    return service.get_member(member_id).to_dict()

@app.put("/api/members/{member_id}")
def update_member(member_id: str, data: MemberUpdate, service: GymService = Depends(get_service)):
    updated = service.update_member(member_id, new_name=data.name, new_type=data.type)
    return updated.to_dict()

@app.delete("/api/members/{member_id}")
def delete_member(member_id: str, service: GymService = Depends(get_service)):
    service.delete_member(member_id)
    return {"message": "Member deleted."}


@app.post("/api/classes", status_code=status.HTTP_201_CREATED)
def create_class(data: ClassCreate, service: GymService = Depends(get_service)):
    workout_class = service.create_class(data.name, data.max_capacity)
    return workout_class.to_dict()

@app.get("/api/classes")
def list_classes(min_capacity: Optional[int] = Query(None), service: GymService = Depends(get_service)):
    classes = service.list_classes(min_capacity=min_capacity)
    return [c.to_dict() for c in classes]

@app.get("/api/classes/{class_id}")
def get_class(class_id: str, service: GymService = Depends(get_service)):
    return service.get_class(class_id).to_dict()

@app.put("/api/classes/{class_id}")
def update_class(class_id: str, data: ClassUpdate, service: GymService = Depends(get_service)):
    updated = service.update_class(class_id, new_name=data.name, new_capacity=data.max_capacity)
    return updated.to_dict()

@app.delete("/api/classes/{class_id}")
def delete_class(class_id: str, service: GymService = Depends(get_service)):
    service.delete_class(class_id)
    return {"message": "Class deleted."}


@app.post("/api/bookings")
def book_class(data: BookingRequest, service: GymService = Depends(get_service)):
    booked = service.book_class(data.member_id, data.class_id)
    return {
        "message": f"Member {data.member_id} successfully booked for class {data.class_id}.",
        "class": booked.to_dict()
    }

@app.delete("/api/bookings")
def cancel_booking(data: BookingRequest, service: GymService = Depends(get_service)):
    updated = service.cancel_booking(data.member_id, data.class_id)
    return {
        "message": "Booking cancelled.",
        "class": updated.to_dict()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8080)
