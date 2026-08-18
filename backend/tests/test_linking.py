"""
Athlete-Professional Linking, Unlinking, and Strict Guard Unit & Integration Tests.
"""

def test_link_coach_success(client, athlete_user, coach_user, auth_headers_athlete, db_session):
    """Tests athlete successfully linking to a coach using valid invite code."""
    payload = {"invite_code": coach_user.invite_code}
    response = client.post("/api/athletes/link", json=payload, headers=auth_headers_athlete)
    assert response.status_code == 200
    assert "Successfully linked" in response.json()["message"]

    db_session.refresh(athlete_user.athlete_profile)
    assert str(athlete_user.athlete_profile.linked_coach_id) == str(coach_user.id)


def test_link_invalid_invite_code_fails(client, auth_headers_athlete):
    """Tests linking with invalid invite code returns 404."""
    payload = {"invite_code": "INVALID_CODE_999"}
    response = client.post("/api/athletes/link", json=payload, headers=auth_headers_athlete)
    assert response.status_code == 404
    assert "Invalid invite code" in response.json()["detail"]


def test_strict_duplicate_coach_link_guard(client, athlete_user, coach_user, auth_headers_athlete, db_session, test_roles):
    """Tests that linking to another coach is blocked if already connected to a coach."""
    # First link to coach_user
    athlete_user.athlete_profile.linked_coach_id = coach_user.id
    db_session.commit()

    # Create a second coach
    import uuid
    from app.models.user import User
    from app.core.security import hash_password
    coach_2 = User(
        id=uuid.uuid4(),
        email="coach2@example.com",
        first_name="David",
        last_name="Trainer",
        hashed_password=hash_password("Password123!"),
        role_id=test_roles["coach"].id,
        is_active=True,
        invite_code="COACH222",
    )
    db_session.add(coach_2)
    db_session.commit()

    # Attempt to link to coach_2 without unlinking coach_user first
    response = client.post("/api/athletes/link", json={"invite_code": "COACH222"}, headers=auth_headers_athlete)
    assert response.status_code == 400
    assert "already linked" in response.json()["detail"]
    assert "Please unlink from your current coach first" in response.json()["detail"]


def test_athlete_self_unlink(client, athlete_user, coach_user, auth_headers_athlete, db_session):
    """Tests athlete self-unlinking from coach creates unlinked notification for coach."""
    athlete_user.athlete_profile.linked_coach_id = coach_user.id
    db_session.commit()

    response = client.post("/api/athletes/unlink", json={"professional_type": "coach"}, headers=auth_headers_athlete)
    assert response.status_code == 200
    assert "Successfully unlinked" in response.json()["message"]

    db_session.refresh(athlete_user.athlete_profile)
    assert athlete_user.athlete_profile.linked_coach_id is None

    # Verify coach received unlinked notification
    from app.models.notification import Notification
    notif = db_session.query(Notification).filter(
        Notification.recipient_id == coach_user.id,
        Notification.risk_level == "unlinked"
    ).first()
    assert notif is not None
    assert "unlinked" in notif.message


def test_coach_remove_athlete_from_roster(client, athlete_user, coach_user, auth_headers_coach, db_session):
    """Tests coach removing athlete from roster."""
    athlete_user.athlete_profile.linked_coach_id = coach_user.id
    db_session.commit()

    response = client.post(
        f"/api/athletes/{athlete_user.id}/unlink",
        headers=auth_headers_coach,
    )
    assert response.status_code == 200
    assert "removed from your roster" in response.json()["message"]

    db_session.refresh(athlete_user.athlete_profile)
    assert athlete_user.athlete_profile.linked_coach_id is None
