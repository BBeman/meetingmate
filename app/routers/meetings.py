from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.meeting import Meeting
from app.models.user import User
from app.schemas.meeting import MeetingCreate, MeetingResponse
from app.services.embeddings import generate_embedding


router = APIRouter(prefix="/meetings", tags=["meetings"])


@router.post("", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
def create_meeting(
    meeting_data: MeetingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Meeting:
    """Ingest a meeting transcript, generate embedding, and store in database."""
    embedding = generate_embedding(meeting_data.transcript)

    meeting = Meeting(
        user_id=current_user.id,
        title=meeting_data.title,
        transcript=meeting_data.transcript,
        embedding=embedding,
    )

    db.add(meeting)
    db.commit()
    db.refresh(meeting)

    return meeting
