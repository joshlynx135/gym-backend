from typing import Annotated
from fastapi import Depends, Request

from services.gym_service import GymService

def get_service(request: Request) -> GymService:
    return GymService(request.app.state.repo)

ServiceDep = Annotated[GymService, Depends(get_service)]