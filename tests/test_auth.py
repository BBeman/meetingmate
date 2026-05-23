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
