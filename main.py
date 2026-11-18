from fastapi import FastAPI

from api.error_handlers import register_error_handlers
from api.routers import classes, members
from repositories.base import GymRepository
from repositories.in_memory import InMemoryGymRepository


def create_app(repo: GymRepository | None = None) -> FastAPI:
    """Build a complete, independent Gym API.
    """
    app = FastAPI(title="Gym API")
    app.state.repo = repo if repo is not None else InMemoryGymRepository()


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8080)