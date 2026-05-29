from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.meeting import Meeting
from app.services.embeddings import generate_embedding_for_query


@dataclass
class MeetingSearchResult:
    """A meeting excerpt with its similarity score from vector search."""
    meeting_id: int
    title: str
    transcript: str
    similarity_score: float


def search_meetings(
    db: Session,
    query: str,
    user_id: int,
    top_k: int = 5,
) -> list[MeetingSearchResult]:
    """
    Search meetings using vector similarity via pgvector.

    Uses cosine distance for semantic similarity. Lower distance = higher similarity.
    Cosine distance ranges 0 (identical) to 2 (opposite). We convert to a 0-1 score.

    Args:
        db: Database session
        query: Natural language search query
        user_id: Only search meetings owned by this user
        top_k: Number of results to return (default 5)

    Returns:
        List of MeetingSearchResult ordered by similarity (highest first)
    """
    # Generate query embedding using Voyage AI with input_type="query".
    # Asymmetric encoding: queries and documents use different embeddings for better retrieval.
    query_embedding = generate_embedding_for_query(query)

    # pgvector's <=> operator computes cosine distance.
    # We filter to user's meetings only and exclude any without embeddings.
    # The cosine_distance function returns distance, not similarity.
    cosine_distance = Meeting.embedding.cosine_distance(query_embedding)

    stmt = (
        select(
            Meeting.id,
            Meeting.title,
            Meeting.transcript,
            cosine_distance.label("distance"),
        )
        .where(Meeting.user_id == user_id)
        .where(Meeting.embedding.isnot(None))
        .order_by(cosine_distance)  # ascending: smallest distance = most similar
        .limit(top_k)
    )

    results = db.execute(stmt).all()

    # Convert cosine distance to similarity score: score = 1 - (distance / 2)
    # Distance 0 becomes score 1.0 (identical), distance 2 becomes score 0.0
    return [
        MeetingSearchResult(
            meeting_id=row.id,
            title=row.title,
            transcript=row.transcript,
            similarity_score=1.0 - (row.distance / 2.0),
        )
        for row in results
    ]
