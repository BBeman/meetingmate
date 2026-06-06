from unittest.mock import patch, MagicMock

import pytest
from fastapi import HTTPException

from app.exceptions import (
    MeetingMateException,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ConflictError,
    ValidationError,
    ExternalServiceError,
    DatabaseError,
    RateLimitError,
    AgentError,
)


# --- Exception Class Tests ---


def test_meetingmate_exception_defaults():
    """Base exception has default status code 500."""
    exc = MeetingMateException("Something went wrong")
    assert exc.message == "Something went wrong"
    assert exc.status_code == 500


def test_meetingmate_exception_custom_status():
    """Base exception accepts custom status code."""
    exc = MeetingMateException("Bad request", status_code=400)
    assert exc.status_code == 400


def test_authentication_error():
    """AuthenticationError returns 401."""
    exc = AuthenticationError()
    assert exc.status_code == 401
    assert exc.message == "Authentication failed"

    exc2 = AuthenticationError("Token expired")
    assert exc2.message == "Token expired"


def test_authorization_error():
    """AuthorizationError returns 403."""
    exc = AuthorizationError()
    assert exc.status_code == 403
    assert exc.message == "Access denied"


def test_not_found_error():
    """NotFoundError returns 404 with resource name."""
    exc = NotFoundError("Meeting")
    assert exc.status_code == 404
    assert exc.message == "Meeting not found"


def test_conflict_error():
    """ConflictError returns 409."""
    exc = ConflictError("Email already registered")
    assert exc.status_code == 409
    assert exc.message == "Email already registered"


def test_validation_error():
    """ValidationError returns 422."""
    exc = ValidationError("Invalid transcript format")
    assert exc.status_code == 422
    assert exc.message == "Invalid transcript format"


def test_external_service_error():
    """ExternalServiceError returns 503 with service name."""
    exc = ExternalServiceError("Anthropic", "Rate limited")
    assert exc.status_code == 503
    assert "Anthropic" in exc.message
    assert "Rate limited" in exc.message


def test_database_error():
    """DatabaseError returns 500."""
    exc = DatabaseError("Connection failed")
    assert exc.status_code == 500
    assert exc.message == "Connection failed"


def test_rate_limit_error():
    """RateLimitError returns 429."""
    exc = RateLimitError()
    assert exc.status_code == 429
    assert exc.message == "Too many requests"


def test_agent_error():
    """AgentError returns 500."""
    exc = AgentError("Max iterations reached")
    assert exc.status_code == 500
    assert exc.message == "Max iterations reached"


# --- Exception Handler Integration Tests ---


def test_custom_exception_handler(client):
    """Custom exceptions return proper JSON response."""
    with patch("app.routers.auth.hash_password") as mock:
        mock.side_effect = MeetingMateException("Test error", status_code=418)
        response = client.post(
            "/auth/signup",
            json={"email": "test@example.com", "password": "password123"},
        )
    assert response.status_code == 418
    assert response.json()["detail"] == "Test error"


def test_validation_error_response_format(client):
    """Validation errors include field-level error details."""
    response = client.post(
        "/auth/signup",
        json={"email": "not-an-email", "password": "short"},
    )
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert "errors" in data
    assert isinstance(data["errors"], list)


def test_missing_required_field_error(client):
    """Missing required fields return 422 with field info."""
    response = client.post("/auth/signup", json={"email": "test@example.com"})
    assert response.status_code == 422
    data = response.json()
    assert "errors" in data
    assert any("password" in e.get("field", "") for e in data["errors"])


def test_invalid_json_body(client):
    """Invalid JSON body returns 422."""
    response = client.post(
        "/auth/signup",
        content="not valid json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


# --- Endpoint Error Scenario Tests ---


def test_login_wrong_password_401(client):
    """Wrong password returns 401 Unauthorized."""
    client.post(
        "/auth/signup",
        json={"email": "user@example.com", "password": "correctpassword"},
    )
    response = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401
    assert "Invalid" in response.json()["detail"]


def test_login_nonexistent_user_401(client):
    """Login with nonexistent user returns 401."""
    response = client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": "anypassword"},
    )
    assert response.status_code == 401


def test_protected_route_no_token_401(client):
    """Accessing protected route without token returns 401."""
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_protected_route_invalid_token_401(client):
    """Accessing protected route with invalid token returns 401."""
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    assert response.status_code == 401


def test_protected_route_malformed_auth_header_401(client):
    """Malformed Authorization header returns 401."""
    response = client.get(
        "/auth/me",
        headers={"Authorization": "NotBearer token"},
    )
    assert response.status_code == 401


def test_duplicate_signup_409(client):
    """Duplicate email signup returns 409 Conflict."""
    client.post(
        "/auth/signup",
        json={"email": "dup@example.com", "password": "password123"},
    )
    response = client.post(
        "/auth/signup",
        json={"email": "dup@example.com", "password": "differentpassword"},
    )
    assert response.status_code == 409
    assert "already registered" in response.json()["detail"]


@patch("app.routers.meetings.generate_embedding", return_value=[0.1] * 1024)
def test_get_nonexistent_meeting_404(mock_embed, client):
    """Getting nonexistent meeting returns 404."""
    client.post(
        "/auth/signup",
        json={"email": "meetinguser@example.com", "password": "password123"},
    )
    login_response = client.post(
        "/auth/login",
        json={"email": "meetinguser@example.com", "password": "password123"},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/meetings/99999", headers=headers)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_create_meeting_without_auth_401(client):
    """Creating meeting without auth returns 401."""
    response = client.post(
        "/meetings",
        json={"title": "Test", "transcript": "Content"},
    )
    assert response.status_code == 401


def test_agent_chat_without_auth_401(client):
    """Agent chat without auth returns 401."""
    response = client.post(
        "/agent/chat",
        json={"question": "What were the action items?"},
    )
    assert response.status_code == 401


def test_agent_chat_empty_question_422(client):
    """Agent chat with empty question returns 422."""
    client.post(
        "/auth/signup",
        json={"email": "agentuser@example.com", "password": "password123"},
    )
    login_response = client.post(
        "/auth/login",
        json={"email": "agentuser@example.com", "password": "password123"},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/agent/chat",
        json={"question": ""},
        headers=headers,
    )
    assert response.status_code == 422


def test_create_meeting_empty_title_422(client):
    """Creating meeting with empty title returns 422."""
    client.post(
        "/auth/signup",
        json={"email": "emptyuser@example.com", "password": "password123"},
    )
    login_response = client.post(
        "/auth/login",
        json={"email": "emptyuser@example.com", "password": "password123"},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/meetings",
        json={"title": "", "transcript": "Some content here"},
        headers=headers,
    )
    assert response.status_code == 422


def test_health_endpoint_always_ok(client):
    """Health endpoint returns 200 even when not authenticated."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_nonexistent_endpoint_404(client):
    """Nonexistent endpoint returns 404."""
    response = client.get("/nonexistent/endpoint")
    assert response.status_code == 404
