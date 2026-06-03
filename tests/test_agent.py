from unittest.mock import MagicMock, patch


def get_auth_header(client) -> dict[str, str]:
    """Helper to create a user, login, and return auth header."""
    client.post(
        "/auth/signup",
        json={"email": "agent_user@example.com", "password": "password123"},
    )
    login_response = client.post(
        "/auth/login",
        json={"email": "agent_user@example.com", "password": "password123"},
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@patch("app.routers.agent.run_agent")
def test_agent_chat_success(mock_run_agent, client):
    """Agent chat returns response from run_agent."""
    mock_run_agent.return_value = "Based on your meetings, the project deadline is next Friday."
    headers = get_auth_header(client)

    response = client.post(
        "/agent/chat",
        json={"question": "When is the project deadline?"},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Based on your meetings, the project deadline is next Friday."
    mock_run_agent.assert_called_once()
    call_args = mock_run_agent.call_args
    assert call_args[0][0] == "When is the project deadline?"


def test_agent_chat_requires_auth(client):
    """Agent chat without auth returns 401."""
    response = client.post(
        "/agent/chat",
        json={"question": "What were the action items from last meeting?"},
    )

    assert response.status_code == 401


@patch("app.routers.agent.run_agent")
def test_agent_chat_empty_question(mock_run_agent, client):
    """Agent chat with empty question returns 422."""
    headers = get_auth_header(client)

    response = client.post(
        "/agent/chat",
        json={"question": ""},
        headers=headers,
    )

    assert response.status_code == 422
    mock_run_agent.assert_not_called()


@patch("app.routers.agent.run_agent")
def test_agent_chat_missing_question(mock_run_agent, client):
    """Agent chat with missing question field returns 422."""
    headers = get_auth_header(client)

    response = client.post(
        "/agent/chat",
        json={},
        headers=headers,
    )

    assert response.status_code == 422
    mock_run_agent.assert_not_called()


@patch("app.routers.agent.run_agent")
def test_agent_chat_passes_user_id(mock_run_agent, client):
    """Agent chat passes correct user_id to run_agent."""
    mock_run_agent.return_value = "No meetings found."
    headers = get_auth_header(client)

    # get current user to know the user_id
    me_response = client.get("/auth/me", headers=headers)
    user_id = me_response.json()["id"]

    client.post(
        "/agent/chat",
        json={"question": "What meetings do I have?"},
        headers=headers,
    )

    call_args = mock_run_agent.call_args
    # run_agent is called with (question, db, user_id)
    assert call_args[0][2] == user_id


@patch("app.routers.agent.run_agent")
def test_agent_chat_with_tool_invocation(mock_run_agent, client):
    """Agent chat handles responses that involve tool calls."""
    # simulate agent response after using search_meetings tool
    mock_run_agent.return_value = (
        "I found 2 meetings discussing the budget. "
        "In the Q3 Planning meeting, the team decided to allocate $50K for marketing."
    )
    headers = get_auth_header(client)

    response = client.post(
        "/agent/chat",
        json={"question": "What did we decide about the budget?"},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "budget" in data["answer"].lower()
    assert "$50K" in data["answer"]


@patch("app.routers.agent.run_agent")
def test_agent_chat_action_items_scenario(mock_run_agent, client):
    """Agent chat handles action item extraction requests."""
    mock_run_agent.return_value = (
        "From your last meeting, I found these action items:\n"
        "1. Alice: Review PR by Friday\n"
        "2. Bob: Update documentation\n"
        "3. Carol: Schedule follow-up meeting"
    )
    headers = get_auth_header(client)

    response = client.post(
        "/agent/chat",
        json={"question": "What are the action items from the last meeting?"},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "action items" in data["answer"].lower()
    assert "Alice" in data["answer"]


@patch("app.routers.agent.run_agent")
def test_agent_chat_decisions_scenario(mock_run_agent, client):
    """Agent chat handles decision summarization requests."""
    mock_run_agent.return_value = (
        "Key decisions from your meetings:\n"
        "1. Team agreed to use Python for the backend\n"
        "2. Launch date set for Q4 2024"
    )
    headers = get_auth_header(client)

    response = client.post(
        "/agent/chat",
        json={"question": "What decisions were made in recent meetings?"},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "decisions" in data["answer"].lower()


@patch("app.routers.agent.run_agent")
def test_agent_chat_no_meetings_found(mock_run_agent, client):
    """Agent chat gracefully handles case when no relevant meetings exist."""
    mock_run_agent.return_value = (
        "I could not find any meetings related to your question. "
        "Please make sure you have ingested meeting transcripts first."
    )
    headers = get_auth_header(client)

    response = client.post(
        "/agent/chat",
        json={"question": "Tell me about the sales strategy discussion"},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "could not find" in data["answer"].lower()


@patch("app.routers.agent.run_agent")
def test_agent_chat_long_question(mock_run_agent, client):
    """Agent chat handles longer questions."""
    mock_run_agent.return_value = "Based on your meetings, here is the summary..."
    headers = get_auth_header(client)

    long_question = (
        "I had a meeting last week about the new product launch and I need to "
        "understand what exactly we decided about the pricing strategy, "
        "the marketing channels we will use, and who is responsible for each task. "
        "Can you help me find all this information?"
    )

    response = client.post(
        "/agent/chat",
        json={"question": long_question},
        headers=headers,
    )

    assert response.status_code == 200
    call_args = mock_run_agent.call_args
    assert call_args[0][0] == long_question
