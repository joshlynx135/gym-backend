import pytest

from repositories.gym_repository import GymRepository
from services.gym_service import GymService


@pytest.fixture
def repo() -> GymRepository:
    # new empty "database" for every single test
    return GymRepository()


@pytest.fixture
def service(repo: GymRepository) -> GymService:
    return GymService(repo)