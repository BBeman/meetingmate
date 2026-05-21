import os
from functools import lru_cache


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self) -> None:
        # Required for database connection
        self.database_url: str = os.environ.get(
            "DATABASE_URL",
            "postgresql://meetingmate:meetingmate@localhost:5432/meetingmate"
        )

    @property
    def database_url_sync(self) -> str:
        """Return sync database URL (psycopg2 uses postgresql://)."""
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance (loaded once per process)."""
    return Settings()
