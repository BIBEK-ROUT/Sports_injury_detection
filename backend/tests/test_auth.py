"""
Authentication & User Account Unit & Integration Tests.
"""

def test_register_athlete_success(client, test_roles):
    """Tests successful registration of a new athlete user."""
    payload = {
        "email": "new_athlete@example.com",
        "password": "SecurePassword123!",
        "first_name": "Jordan",
        "last_name": "Smith",
        "role_id": test_roles["athlete"].id,
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == payload["email"]
    assert data["first_name"] == payload["first_name"]
    assert data["is_active"] is True
    assert "hashed_password" not in data


def test_register_duplicate_email_fails(client, athlete_user, test_roles):
    """Tests registration rejection when email already exists."""
    payload = {
        "email": athlete_user.email,
        "password": "AnyPassword123!",
        "first_name": "Duplicate",
        "last_name": "User",
        "role_id": test_roles["athlete"].id,
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_login_success(client, athlete_user):
    """Tests valid login returns a JWT bearer access token."""
    response = client.post(
        "/api/auth/login",
        data={"username": athlete_user.email, "password": "Password123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_password_fails(client, athlete_user):
    """Tests login with incorrect password returns 401 Unauthorized."""
    response = client.post(
        "/api/auth/login",
        data={"username": athlete_user.email, "password": "WrongPassword!"},
    )
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


def test_login_deactivated_account_fails(client, athlete_user, db_session):
    """Tests login with deactivated account returns 403 with support email."""
    athlete_user.is_active = False
    db_session.commit()

    response = client.post(
        "/api/auth/login",
        data={"username": athlete_user.email, "password": "Password123!"},
    )
    assert response.status_code == 403
    assert "sportguardsupport@gmail.com" in response.json()["detail"]


def test_get_current_user_me(client, athlete_user, auth_headers_athlete):
    """Tests /api/auth/me returns current logged-in user details."""
    response = client.get("/api/auth/me", headers=auth_headers_athlete)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == athlete_user.email
    assert data["role"]["name"] == "athlete"
