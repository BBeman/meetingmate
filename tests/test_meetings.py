from unittest.mock import patch


MOCK_EMBEDDING = [0.1] * 1024  # 1024-dim vector to match voyage-3 model


def get_auth_header(client) -> dict[str, str]:
    """Helper to create a user, login, and return auth header."""
    client.post(
        "/auth/signup",
        json={"email": "meeting_user@example.com", "password": "password123"},
    )
    login_response = client.post(
        "/auth/login",
        json={"email": "meeting_user@example.com", "password": "password123"},
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@patch("app.routers.meetings.generate_embedding", return_value=MOCK_EMBEDDING)
def test_create_meeting_success(mock_embed, client):
    """Successful meeting creation returns meeting data with generated ID."""
    headers = get_auth_header(client)

    response = client.post(
        "/meetings",
        json={
            "title": "Weekly Standup",
            "transcript": "Alice: We shipped the feature. Bob: Nice work!",
        },
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Weekly Standup"
    assert data["transcript"] == "Alice: We shipped the feature. Bob: Nice work!"
    assert "id" in data
    assert "user_id" in data
    assert "created_at" in data
    mock_embed.assert_called_once_with("Alice: We shipped the feature. Bob: Nice work!")


@patch("app.routers.meetings.generate_embedding", return_value=MOCK_EMBEDDING)
def test_create_meeting_requires_auth(mock_embed, client):
    """Creating a meeting without auth returns 401."""
    response = client.post(
        "/meetings",
        json={
            "title": "Secret Meeting",
            "transcript": "Confidential discussion here.",
        },
    )

    assert response.status_code == 401
    mock_embed.assert_not_called()


@patch("app.routers.meetings.generate_embedding", return_value=MOCK_EMBEDDING)
def test_create_meeting_empty_title(mock_embed, client):
    """Creating a meeting with empty title returns 422."""
    headers = get_auth_header(client)

    response = client.post(
        "/meetings",
        json={
            "title": "",
            "transcript": "Some transcript content here.",
        },
        headers=headers,
    )

    assert response.status_code == 422
    mock_embed.assert_not_called()


@patch("app.routers.meetings.generate_embedding", return_value=MOCK_EMBEDDING)
def test_create_meeting_empty_transcript(mock_embed, client):
    """Creating a meeting with empty transcript returns 422."""
    headers = get_auth_header(client)

    response = client.post(
        "/meetings",
        json={
            "title": "Valid Title",
            "transcript": "",
        },
        headers=headers,
    )

    assert response.status_code == 422
    mock_embed.assert_not_called()


@patch("app.routers.meetings.generate_embedding", return_value=MOCK_EMBEDDING)
def test_create_meeting_missing_fields(mock_embed, client):
    """Creating a meeting with missing fields returns 422."""
    headers = get_auth_header(client)

    response = client.post(
        "/meetings",
        json={"title": "Only Title"},
        headers=headers,
    )

    assert response.status_code == 422

    response = client.post(
        "/meetings",
        json={"transcript": "Only transcript"},
        headers=headers,
    )

    assert response.status_code == 422
    mock_embed.assert_not_called()


@patch("app.routers.meetings.generate_embedding", return_value=MOCK_EMBEDDING)
def test_create_meeting_associates_with_user(mock_embed, client):
    """Meeting is correctly associated with the authenticated user."""
    headers = get_auth_header(client)

    response = client.post(
        "/meetings",
        json={
            "title": "Team Sync",
            "transcript": "Discussion about project timeline.",
        },
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()

    # Get current user to verify association
    me_response = client.get("/auth/me", headers=headers)
    user_data = me_response.json()

    assert data["user_id"] == user_data["id"]
