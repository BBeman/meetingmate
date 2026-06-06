import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.database import check_database_connection
from app.exceptions import MeetingMateException
from app.routers import agent, auth, meetings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MeetingMate")

app.include_router(agent.router)
app.include_router(auth.router)
app.include_router(meetings.router)


@app.exception_handler(MeetingMateException)
async def meetingmate_exception_handler(
    request: Request,
    exc: MeetingMateException,
) -> JSONResponse:
    """Handle all custom MeetingMate exceptions with consistent JSON responses."""
    logger.warning(f"MeetingMate error: {exc.message} (status={exc.status_code})")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Handle Pydantic validation errors with cleaner error messages."""
    errors = []
    for error in exc.errors():
        loc = " -> ".join(str(x) for x in error["loc"])
        errors.append({"field": loc, "message": error["msg"]})
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation error", "errors": errors},
    )


@app.exception_handler(Exception)
async def general_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Catch-all handler for unexpected errors. Logs stack trace, returns generic message."""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred"},
    )


@app.get("/health")
def health() -> dict[str, str]:
    """Basic health check that verifies the API is running."""
    return {"status": "ok"}


@app.get("/health/db")
def health_db() -> dict[str, str | bool]:
    """Health check that verifies database connectivity."""
    db_ok = check_database_connection()
    return {
        "status": "ok" if db_ok else "error",
        "database_connected": db_ok,
    }
