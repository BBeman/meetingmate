from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.meeting import Meeting
from app.models.user import User
from app.schemas.meeting import MeetingCreate, MeetingListResponse, MeetingResponse
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


@router.get("", response_model=MeetingListResponse)
def list_meetings(
    skip: int = Query(default=0, ge=0, description="Number of items to skip"),
    limit: int = Query(default=20, ge=1, le=100, description="Number of items to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """List all meetings for the current user with pagination."""
    query = db.query(Meeting).filter(Meeting.user_id == current_user.id)
    total = query.count()
    meetings = query.order_by(Meeting.created_at.desc()).offset(skip).limit(limit).all()

    return {"meetings": meetings, "total": total, "skip": skip, "limit": limit}


@router.get("/{meeting_id}", response_model=MeetingResponse)
def get_meeting(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Meeting:
    """Retrieve a single meeting by ID. Users can only access their own meetings."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()

    if meeting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )

    # ensure user can only access their own meetings
    if meeting.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )

    return meeting
