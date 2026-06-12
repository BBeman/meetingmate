from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker, declarative_base

from app.config import get_settings

settings = get_settings()

# Create database engine with connection pooling
engine = create_engine(
    settings.database_url_sync,
    pool_pre_ping=True,  # verify connections before using them
    pool_size=5,
    max_overflow=10,
)

# Session factory for creating database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all ORM models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency that provides a database session and closes it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> bool:
    """Verify database is reachable by executing a simple query."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
