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


# --- List Meetings Tests ---


@patch("app.routers.meetings.generate_embedding", return_value=MOCK_EMBEDDING)
def test_list_meetings_success(mock_embed, client):
    """List meetings returns user's meetings with pagination info."""
    headers = get_auth_header(client)

    # create a few meetings
    for i in range(3):
        client.post(
            "/meetings",
            json={"title": f"Meeting {i}", "transcript": f"Transcript {i}"},
            headers=headers,
        )

    response = client.get("/meetings", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["meetings"]) == 3
    assert data["skip"] == 0
    assert data["limit"] == 20


@patch("app.routers.meetings.generate_embedding", return_value=MOCK_EMBEDDING)
def test_list_meetings_pagination(mock_embed, client):
    """List meetings respects skip and limit parameters."""
    headers = get_auth_header(client)

    # create 5 meetings
    for i in range(5):
        client.post(
            "/meetings",
            json={"title": f"Meeting {i}", "transcript": f"Transcript {i}"},
            headers=headers,
        )

    # get first 2
    response = client.get("/meetings?skip=0&limit=2", headers=headers)
    data = response.json()
    assert data["total"] == 5
    assert len(data["meetings"]) == 2
    assert data["skip"] == 0
    assert data["limit"] == 2

    # get next 2
    response = client.get("/meetings?skip=2&limit=2", headers=headers)
    data = response.json()
    assert data["total"] == 5
    assert len(data["meetings"]) == 2
    assert data["skip"] == 2


def test_list_meetings_requires_auth(client):
    """List meetings without auth returns 401."""
    response = client.get("/meetings")
    assert response.status_code == 401


@patch("app.routers.meetings.generate_embedding", return_value=MOCK_EMBEDDING)
def test_list_meetings_only_shows_own(mock_embed, client):
    """Users only see their own meetings, not other users' meetings."""
    # create meeting for first user
    headers1 = get_auth_header(client)
    client.post(
        "/meetings",
        json={"title": "User1 Meeting", "transcript": "User1 content"},
        headers=headers1,
    )

    # create second user and their meeting
    client.post(
        "/auth/signup",
        json={"email": "other_user@example.com", "password": "password123"},
    )
    login_response = client.post(
        "/auth/login",
        json={"email": "other_user@example.com", "password": "password123"},
    )
    headers2 = {"Authorization": f"Bearer {login_response.json()['access_token']}"}
    client.post(
        "/meetings",
        json={"title": "User2 Meeting", "transcript": "User2 content"},
        headers=headers2,
    )

    # user1 should only see their meeting
    response = client.get("/meetings", headers=headers1)
    data = response.json()
    assert data["total"] == 1
    assert data["meetings"][0]["title"] == "User1 Meeting"

    # user2 should only see their meeting
    response = client.get("/meetings", headers=headers2)
    data = response.json()
    assert data["total"] == 1
    assert data["meetings"][0]["title"] == "User2 Meeting"


@patch("app.routers.meetings.generate_embedding", return_value=MOCK_EMBEDDING)
def test_list_meetings_empty(mock_embed, client):
    """List meetings returns empty list when user has no meetings."""
    headers = get_auth_header(client)

    response = client.get("/meetings", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["meetings"]) == 0


# --- Get Meeting Tests ---


@patch("app.routers.meetings.generate_embedding", return_value=MOCK_EMBEDDING)
def test_get_meeting_success(mock_embed, client):
    """Get meeting by ID returns the meeting data."""
    headers = get_auth_header(client)

    create_response = client.post(
        "/meetings",
        json={"title": "Specific Meeting", "transcript": "Detailed transcript here"},
        headers=headers,
    )
    meeting_id = create_response.json()["id"]

    response = client.get(f"/meetings/{meeting_id}", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == meeting_id
    assert data["title"] == "Specific Meeting"
    assert data["transcript"] == "Detailed transcript here"


def test_get_meeting_requires_auth(client):
    """Get meeting without auth returns 401."""
    response = client.get("/meetings/1")
    assert response.status_code == 401


@patch("app.routers.meetings.generate_embedding", return_value=MOCK_EMBEDDING)
def test_get_meeting_not_found(mock_embed, client):
    """Get nonexistent meeting returns 404."""
    headers = get_auth_header(client)

    response = client.get("/meetings/99999", headers=headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Meeting not found"


@patch("app.routers.meetings.generate_embedding", return_value=MOCK_EMBEDDING)
def test_get_meeting_cannot_access_others(mock_embed, client):
    """Users cannot access other users' meetings (returns 404)."""
    # create meeting for first user
    headers1 = get_auth_header(client)
    create_response = client.post(
        "/meetings",
        json={"title": "Private Meeting", "transcript": "Private content"},
        headers=headers1,
    )
    meeting_id = create_response.json()["id"]

    # create second user
    client.post(
        "/auth/signup",
        json={"email": "attacker@example.com", "password": "password123"},
    )
    login_response = client.post(
        "/auth/login",
        json={"email": "attacker@example.com", "password": "password123"},
    )
    headers2 = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    # second user should not be able to access first user's meeting
    response = client.get(f"/meetings/{meeting_id}", headers=headers2)

    assert response.status_code == 404
    assert response.json()["detail"] == "Meeting not found"
