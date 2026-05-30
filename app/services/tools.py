import json
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.meeting import Meeting
from app.services.embeddings import generate_embedding_for_query, get_anthropic_client


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


@dataclass
class ActionItem:
    """An extracted action item from a meeting transcript."""
    description: str
    assignee: str | None
    deadline: str | None


# System prompt engineered for precise action extraction.
# We explicitly instruct Claude to:
# 1. Only extract explicit action items (tasks someone committed to do)
# 2. Not invent assignees or deadlines when none are mentioned
# 3. Return a specific JSON format for reliable parsing
# 4. Distinguish action items from general discussion or decisions
EXTRACT_ACTIONS_SYSTEM_PROMPT = """You are an expert meeting analyst. Your task is to extract clear, actionable items from meeting transcripts.

An action item is a specific task that someone has agreed to complete. Look for:
- Explicit commitments ("I will...", "I'll take care of...")
- Delegated tasks ("Can you...", "Please handle...")
- Volunteered work ("Let me...", "I can do...")

For each action item, extract:
1. description: What needs to be done (be specific and concise)
2. assignee: The person responsible (use their name if mentioned, null if unclear)
3. deadline: When it should be completed (use exact wording from transcript if given, null if not mentioned)

Rules:
- Only extract explicit action items, not general discussion points
- Do not infer or fabricate assignees or deadlines
- If multiple people might be responsible, use the most likely one or null
- Keep descriptions actionable and to the point

Return a JSON array of action items. If no action items are found, return an empty array."""


EXTRACT_ACTIONS_USER_PROMPT = """Extract action items from this meeting transcript:

<transcript>
{transcript}
</transcript>

Return ONLY a JSON array with this exact structure (no markdown, no explanation):
[{{"description": "task description", "assignee": "person or null", "deadline": "deadline or null"}}]"""


def extract_actions(transcript: str) -> list[ActionItem]:
    """
    Extract action items from a meeting transcript using Claude.

    Uses Claude to parse natural language and identify explicit action items,
    returning structured data including assignee and deadline when mentioned.
    """
    client = get_anthropic_client()

    # Claude Sonnet 4 is used for reliable structured extraction with good accuracy.
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        system=EXTRACT_ACTIONS_SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": EXTRACT_ACTIONS_USER_PROMPT.format(transcript=transcript)}
        ],
    )

    # Extract text from response content blocks
    response_text = "".join(
        block.text for block in response.content if hasattr(block, "text")
    )

    # Parse JSON response from Claude
    try:
        actions_data = json.loads(response_text.strip())
    except json.JSONDecodeError:
        # Claude sometimes wraps JSON in markdown code blocks
        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if json_match:
            actions_data = json.loads(json_match.group())
        else:
            return []

    return [
        ActionItem(
            description=item.get("description", ""),
            assignee=item.get("assignee"),
            deadline=item.get("deadline"),
        )
        for item in actions_data
        if item.get("description")
    ]
