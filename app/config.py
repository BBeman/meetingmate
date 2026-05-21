import os
from functools import lru_cache


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self) -> None:
        self.database_url: str = os.environ.get(
            "DATABASE_URL",
            "postgresql://meetingmate:meetingmate@localhost:5432/meetingmate"
        )
        # JWT signing key, must be set in production
        self.jwt_secret: str = os.environ.get("JWT_SECRET", "")
        self.jwt_algorithm: str = "HS256"
        # Token expires in 30 minutes by default
        self.jwt_expire_minutes: int = 30

    @property
    def database_url_sync(self) -> str:
        """Return sync database URL (psycopg2 uses postgresql://)."""
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance (loaded once per process)."""
    return Settings()
