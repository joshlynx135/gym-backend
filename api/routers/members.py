from typing import Optional

from fastapi import APIRouter, status

from api.dependencies import ServiceDep
from api.schemas import MemberCreate, MemberUpdate
router = APIRouter(prefix="/api/members", tags=["Members"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_member(data: MemberCreate, service: ServiceDep):
    return service.create_member(data.name, data.type).to_dict()

@router.get("")
def list_members(service: ServiceDep, type: Optional[str] = None):
    # Optional filter: GET /api/members?type=premium
    return [m.to_dict() for m in service.list_members(member_type=type)]


@router.get("/{member_id}")
def get_member(member_id: str, service: ServiceDep):
    return service.get_member(member_id).to_dict()


@router.put("/{member_id}")
def update_member(member_id: str, data: MemberUpdate, service: ServiceDep):
    # Fields the client did not send arrive as None; the service leaves those unchanged
    return service.update_member(member_id, new_name=data.name, new_type=data.type).to_dict()

@router.delete("/{member_id}")
def delete_member(member_id: str, service: ServiceDep):
    service.delete_member(member_id)
    return {"message": "Member deleted."}