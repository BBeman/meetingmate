import anthropic
import voyageai

from app.config import get_settings

# Voyage AI is Anthropic's recommended embedding provider for Claude-based apps.
# voyage-3 produces 1024-dim vectors, a good balance of quality and storage size.
# For semantic search over meeting transcripts, dense vectors outperform sparse.
EMBEDDING_MODEL = "voyage-3"
EMBEDDING_DIMENSIONS = 1024


def get_anthropic_client() -> anthropic.Anthropic:
    """Create an Anthropic client using the API key from settings."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def get_voyage_client() -> voyageai.Client:
    """Create a Voyage AI client for embedding generation."""
    settings = get_settings()
    if not settings.voyage_api_key:
        raise ValueError("VOYAGE_API_KEY environment variable is not set")
    return voyageai.Client(api_key=settings.voyage_api_key)


def generate_embedding(text: str) -> list[float]:
    """
    Generate a vector embedding for the given text.

    Uses Voyage AI, Anthropic's recommended embedding model for semantic search.
    Returns a 1024-dimensional vector suitable for pgvector storage.
    """
    client = get_voyage_client()

    # input_type="document" optimizes embeddings for stored content.
    # Voyage uses asymmetric encoding: docs and queries are embedded differently.
    result = client.embed(
        texts=[text],
        model=EMBEDDING_MODEL,
        input_type="document",
    )

    # Result contains list of embeddings matching input order
    return result.embeddings[0]


def generate_embedding_for_query(query: str) -> list[float]:
    """
    Generate embedding optimized for search queries.

    Voyage recommends "query" input_type for retrieval queries.
    This asymmetric approach improves search accuracy over symmetric encoding.
    """
    client = get_voyage_client()

    result = client.embed(
        texts=[query],
        model=EMBEDDING_MODEL,
        input_type="query",
    )

    return result.embeddings[0]
