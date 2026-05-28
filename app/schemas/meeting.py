from datetime import datetime

from pydantic import BaseModel, Field


class MeetingCreate(BaseModel):
    """Request body for creating a new meeting from a transcript."""
    title: str = Field(min_length=1, max_length=255)
    transcript: str = Field(min_length=1)


class MeetingResponse(BaseModel):
    """Meeting data returned to clients (excludes embedding)."""
    id: int
    user_id: int
    title: str
    transcript: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MeetingListResponse(BaseModel):
    """Paginated list of meetings."""
    meetings: list[MeetingResponse]
    total: int
    skip: int
    limit: int
