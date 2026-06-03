from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.agent import AgentRequest, AgentResponse
from app.services.agent import run_agent


router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/chat", response_model=AgentResponse)
def chat(
    request: AgentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AgentResponse:
    """Ask the MeetingMate agent a question about your meetings."""
    answer = run_agent(request.question, db, current_user.id)
    return AgentResponse(answer=answer)
