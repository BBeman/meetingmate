def test_signup_success(client):
    """Successful signup returns user data without password."""
    response = client.post(
        "/auth/signup",
        json={"email": "test@example.com", "password": "securepassword123"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data
    assert "created_at" in data
    assert "password" not in data
    assert "hashed_password" not in data


def test_signup_duplicate_email(client):
    """Signing up with an existing email returns 409 Conflict."""
    user_data = {"email": "duplicate@example.com", "password": "password123"}

    response1 = client.post("/auth/signup", json=user_data)
    assert response1.status_code == 201

    response2 = client.post("/auth/signup", json=user_data)
    assert response2.status_code == 409
    assert "already registered" in response2.json()["detail"]


def test_signup_invalid_email(client):
    """Signup with invalid email format returns 422."""
    response = client.post(
        "/auth/signup",
        json={"email": "not-an-email", "password": "password123"},
    )

    assert response.status_code == 422


def test_login_success(client):
    """Successful login returns JWT access token."""
    # First create a user
    client.post(
        "/auth/signup",
        json={"email": "login@example.com", "password": "mypassword123"},
    )

    # Then login
    response = client.post(
        "/auth/login",
        json={"email": "login@example.com", "password": "mypassword123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 0


def test_login_invalid_password(client):
    """Login with wrong password returns 401 Unauthorized."""
    # First create a user
    client.post(
        "/auth/signup",
        json={"email": "wrongpass@example.com", "password": "correctpassword"},
    )

    # Try login with wrong password
    response = client.post(
        "/auth/login",
        json={"email": "wrongpass@example.com", "password": "wrongpassword"},
    )

    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_login_nonexistent_user(client):
    """Login with nonexistent email returns 401 Unauthorized."""
    response = client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": "somepassword"},
    )

    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_get_me_success(client):
    """GET /auth/me returns current user when authenticated."""
    # Create user and login
    client.post(
        "/auth/signup",
        json={"email": "me@example.com", "password": "password123"},
    )
    login_response = client.post(
        "/auth/login",
        json={"email": "me@example.com", "password": "password123"},
    )
    token = login_response.json()["access_token"]

    # Access protected route
    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@example.com"
    assert "id" in data
    assert "created_at" in data
    assert "password" not in data
    assert "hashed_password" not in data


def test_get_me_no_token(client):
    """GET /auth/me without token returns 401 (missing credentials)."""
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_get_me_invalid_token(client):
    """GET /auth/me with invalid token returns 401."""
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert "Invalid or expired token" in response.json()["detail"]


def test_get_me_malformed_header(client):
    """GET /auth/me with malformed auth header returns 401."""
    response = client.get(
        "/auth/me",
        headers={"Authorization": "NotBearer sometoken"},
    )

    assert response.status_code == 401
