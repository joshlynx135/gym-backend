from fastapi import APIRouter

from api.dependencies import ServiceDep
from api.schemas import TransferRequest

router = APIRouter(prefix="/api/bookings", tags=["Bookings"])


@router.post("/transfer")
def transfer_booking(data: TransferRequest, service: ServiceDep):
    source, target = service.transfer_booking(data.member_id, data.from_class_id, data.to_class_id)
    return {
        "message": f"Member {data.member_id} moved from class {source.id} to class {target.id}.",
        "from_class": source.to_dict(),
        "to_class": target.to_dict(),
    }