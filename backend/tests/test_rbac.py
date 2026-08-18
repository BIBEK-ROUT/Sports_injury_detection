"""
Role-Based Access Control (RBAC) & Admin Control Unit & Integration Tests.
"""

def test_athlete_forbidden_from_admin_stats(client, auth_headers_athlete):
    """Tests that non-admin athlete receives 403 Forbidden on Admin stats."""
    response = client.get("/api/admin/stats", headers=auth_headers_athlete)
    assert response.status_code == 403
    assert "Administrator privileges required" in response.json()["detail"]


def test_admin_can_access_platform_stats(client, auth_headers_admin):
    """Tests that admin can retrieve platform stats and AI telemetry."""
    response = client.get("/api/admin/stats", headers=auth_headers_admin)
    assert response.status_code == 200
    data = response.json()
    assert "total_users" in data
    assert "users_by_role" in data
    assert "ai_usage" in data


def test_admin_toggle_system_config(client, auth_headers_admin):
    """Tests admin toggling a system configuration flag."""
    payload = {"key": "ai_chatbot_enabled", "value": "false"}
    response = client.post("/api/admin/config", json=payload, headers=auth_headers_admin)
    assert response.status_code == 200
    assert "updated" in response.json()["message"]

    # Verify public config reflects updated state
    public_res = client.get("/api/public/config")
    assert public_res.status_code == 200
    assert public_res.json()["ai_chatbot_enabled"] == "false"


def test_admin_deactivate_and_activate_user(client, athlete_user, auth_headers_admin, db_session):
    """Tests admin toggling user active status."""
    # Deactivate user
    deact_payload = {"is_active": False}
    response = client.patch(f"/api/admin/users/{athlete_user.id}/status", json=deact_payload, headers=auth_headers_admin)
    assert response.status_code == 200

    db_session.refresh(athlete_user)
    assert athlete_user.is_active is False

    # Reactivate user
    react_payload = {"is_active": True}
    response = client.patch(f"/api/admin/users/{athlete_user.id}/status", json=react_payload, headers=auth_headers_admin)
    assert response.status_code == 200

    db_session.refresh(athlete_user)
    assert athlete_user.is_active is True
