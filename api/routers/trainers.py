from fastapi import APIRouter, status

from api.dependencies import ServiceDep
from api.schemas import TrainerCreate, TrainerUpdate

router = APIRouter(prefix="/api/trainers", tags=["Trainers"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_trainer(data: TrainerCreate, service: ServiceDep):
    return service.create_trainer(data.name).to_dict()


@router.get("")
def list_trainers(service: ServiceDep):
    return [trainer.to_dict() for trainer in service.list_trainers()]


@router.get("/{trainer_id}")
def get_trainer(trainer_id: str, service: ServiceDep):
    return service.get_trainer(trainer_id).to_dict()


@router.put("/{trainer_id}")
def update_trainer(trainer_id: str, data: TrainerUpdate, service: ServiceDep):
    return service.update_trainer(trainer_id, new_name=data.name).to_dict()


@router.delete("/{trainer_id}")
def delete_trainer(trainer_id: str, service: ServiceDep):
    service.delete_trainer(trainer_id)
    return {"message": "Trainer deleted."}