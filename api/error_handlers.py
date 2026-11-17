import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from domain.exceptions import NotFoundError, RuleViolationError, ValidationError

logger = logging.getLogger("gym_api")


def _error(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": message})


def register_error_handlers(app: FastAPI) -> None:

    # Domain errors
    @app.exception_handler(NotFoundError)
    async def handle_not_found(request: Request, exc: NotFoundError):
        return _error(404, str(exc))

    @app.exception_handler(RuleViolationError)
    async def handle_rule_violation(request: Request, exc: RuleViolationError):
        return _error(409, str(exc))

    @app.exception_handler(ValidationError)
    async def handle_domain_validation(request: Request, exc: ValidationError):
        return _error(400, str(exc))

    # FastAPI's own validation (bad JSON, wrong types, missing fields)
    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(request: Request, exc: RequestValidationError):
        problems = [
            f"{'.'.join(str(part) for part in err['loc'])}: {err['msg']}"
            for err in exc.errors()
        ]
        return _error(400, "; ".join(problems))

    # Unknown URL (404) or wrong HTTP method (405)
    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException):
        return _error(exc.status_code, str(exc.detail))

    # any bug we didn't anticipate 
    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception):
        # Log the full traceback for us, but never leak internals to the client
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return _error(500, "Internal server error.")