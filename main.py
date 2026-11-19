from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.error_handlers import register_error_handlers
from api.routers import classes, members, trainers
from repositories.database import create_db_engine, create_session_factory, get_database_url
from repositories.schema import upgrade_schema


def create_app(database_url: str | None = None) -> FastAPI:
    """Build a Gym API that stores its data in PostgreSQL."""
    url = database_url or get_database_url()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup: create or update the tables, then open the connection pool
        upgrade_schema(url)
        engine = create_db_engine(url)
        app.state.session_factory = create_session_factory(engine)
        yield  # the application serves requests while we are suspended here
        # Shutdown: close every pooled connection
        engine.dispose()

    app = FastAPI(title="Gym API", lifespan=lifespan)
    register_error_handlers(app)
    app.include_router(members.router)
    app.include_router(classes.router)
    app.include_router(trainers.router)
    return app


# The instance uvicorn serves. Creating it does not touch the database; that happens at startup.
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8080)