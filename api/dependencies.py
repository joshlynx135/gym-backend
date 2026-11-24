from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request

from repositories.sql_repository import SqlGymRepository
from services.gym_service import GymService


def get_service(request: Request) -> Iterator[GymService]:
    # One database session per request. The service commits or rolls back its own work,
    # so this function only has to release the session when the request is over.
    session = request.app.state.session_factory()
    try:
        yield GymService(SqlGymRepository(session))
    finally:
        session.close()


# `service: ServiceDep` in a route means: "call get_service() and give me the result"
ServiceDep = Annotated[GymService, Depends(get_service)]