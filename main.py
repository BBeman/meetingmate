from fastapi import FastAPI

from app.database import check_database_connection
from app.routers import auth, meetings

app = FastAPI(title="MeetingMate")

app.include_router(auth.router)
app.include_router(meetings.router)


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
