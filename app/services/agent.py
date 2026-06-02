import json
from dataclasses import asdict
from typing import Any

from sqlalchemy.orm import Session

from app.services.embeddings import get_anthropic_client
from app.services.tools import (
    ActionItem,
    Decision,
    MeetingSearchResult,
    extract_actions,
    search_meetings,
    summarise_decisions,
)


# Tool definitions for Claude. Each tool maps to a function in tools.py.
# Claude uses these schemas to decide which tool to call and with what arguments.
TOOL_DEFINITIONS = [
    {
        "name": "search_meetings",
        "description": (
            "Search through the user's meeting transcripts using semantic similarity. "
            "Use this to find relevant meetings based on topics, keywords, or concepts. "
            "Returns meeting excerpts ranked by relevance."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query to find relevant meetings",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return (default 5, max 10)",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "extract_actions",
        "description": (
            "Extract action items from a meeting transcript. "
            "Returns a list of tasks with assignees and deadlines when mentioned. "
            "Use this when the user asks about tasks, to-dos, or action items."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "transcript": {
                    "type": "string",
                    "description": "The meeting transcript text to analyze",
                },
            },
            "required": ["transcript"],
        },
    },
    {
        "name": "summarise_decisions",
        "description": (
            "Identify and summarize key decisions from a meeting transcript. "
            "Returns decisions with context and participants involved. "
            "Use this when the user asks about decisions, agreements, or conclusions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "transcript": {
                    "type": "string",
                    "description": "The meeting transcript text to analyze",
                },
            },
            "required": ["transcript"],
        },
    },
]


AGENT_SYSTEM_PROMPT = """You are MeetingMate, an AI assistant that helps users understand and extract insights from their meeting transcripts.

You have access to the following tools:
1. search_meetings: Search through stored meeting transcripts by topic or keyword
2. extract_actions: Pull out action items from a specific meeting transcript
3. summarise_decisions: Identify key decisions made during a meeting

When answering user questions:
- Use search_meetings first to find relevant meetings if the user asks about past discussions
- Use extract_actions when asked about tasks, to-dos, or what needs to be done
- Use summarise_decisions when asked about what was decided or agreed upon
- You can combine tools: search first, then analyze the found transcripts

Always provide clear, concise answers based on the actual meeting content.
If no relevant information is found, say so honestly."""


def _serialize_tool_result(result: Any) -> str:
    """Convert tool results to JSON string for Claude."""
    if isinstance(result, list):
        # Handle lists of dataclass results
        if result and hasattr(result[0], "__dataclass_fields__"):
            return json.dumps([asdict(item) for item in result])
        return json.dumps(result)
    if hasattr(result, "__dataclass_fields__"):
        return json.dumps(asdict(result))
    return json.dumps(result)


def _execute_tool(
    tool_name: str,
    tool_input: dict[str, Any],
    db: Session,
    user_id: int,
) -> list[MeetingSearchResult] | list[ActionItem] | list[Decision]:
    """Execute a tool call and return the result."""
    if tool_name == "search_meetings":
        query = tool_input["query"]
        top_k = min(tool_input.get("top_k", 5), 10)  # cap at 10 results
        return search_meetings(db, query, user_id, top_k)

    elif tool_name == "extract_actions":
        transcript = tool_input["transcript"]
        return extract_actions(transcript)

    elif tool_name == "summarise_decisions":
        transcript = tool_input["transcript"]
        return summarise_decisions(transcript)

    else:
        raise ValueError(f"Unknown tool: {tool_name}")


def run_agent(
    question: str,
    db: Session,
    user_id: int,
    max_iterations: int = 10,
) -> str:
    """
    Run the MeetingMate agent to answer a user question.

    Implements an agentic loop: sends the question to Claude, handles any tool calls,
    and continues until Claude returns a final text response or max iterations reached.

    Args:
        question: The user's question about their meetings
        db: Database session for search_meetings tool
        user_id: Current user's ID (for scoping meeting searches)
        max_iterations: Safety limit to prevent infinite loops

    Returns:
        Claude's final text response answering the question
    """
    client = get_anthropic_client()

    # Start with the user's question
    messages: list[dict[str, Any]] = [{"role": "user", "content": question}]

    for _ in range(max_iterations):
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=AGENT_SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )

        # Check if Claude wants to use tools
        if response.stop_reason == "tool_use":
            # Build assistant message with all content blocks (text + tool_use)
            assistant_content = []
            tool_results = []

            for block in response.content:
                if block.type == "text":
                    assistant_content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    assistant_content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })

                    # Execute the tool and collect result
                    try:
                        result = _execute_tool(block.name, block.input, db, user_id)
                        result_str = _serialize_tool_result(result)
                    except Exception as e:
                        result_str = json.dumps({"error": str(e)})

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str,
                    })

            # Add assistant message and tool results to conversation
            messages.append({"role": "assistant", "content": assistant_content})
            messages.append({"role": "user", "content": tool_results})

        else:
            # Claude finished with a text response (stop_reason is "end_turn" or similar)
            final_text = ""
            for block in response.content:
                if block.type == "text":
                    final_text += block.text

            return final_text

    # Safety: if we hit max iterations, return whatever we have
    return "I was unable to complete the request within the allowed number of steps."
