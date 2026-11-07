from fastapi import FastAPI

from api.error_handlers import register_error_handlers
from api.routers import classes, members
from repositories.gym_repository import GymRepository


def create_app(repo: GymRepository | None = None) -> FastAPI:
    
    app = FastAPI(title="Gym API")
    app.state.repo = repo if repo is not None else GymRepository()
    register_error_handlers(app)
    app.include_router(members.router)
    app.include_router(classes.router)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8080)