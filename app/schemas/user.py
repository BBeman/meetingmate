from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    """Request body for creating a new user account."""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User data returned to clients (excludes password)."""
    id: int
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}
