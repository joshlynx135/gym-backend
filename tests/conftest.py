import pytest

from repositories.in_memory import InMemoryGymRepository
from services.gym_service import GymService


@pytest.fixture
def repo() -> InMemoryGymRepository:
    # A brand-new, empty store for every single test
    return InMemoryGymRepository()


@pytest.fixture
def service(repo: InMemoryGymRepository) -> GymService:
    # Dependency injection: we hand the service its storage
    return GymService(repo)