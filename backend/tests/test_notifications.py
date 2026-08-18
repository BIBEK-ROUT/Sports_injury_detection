"""
Notification System Unit & Integration Tests.
"""

import uuid
from datetime import datetime
from app.models.notification import Notification


def test_get_notifications_for_coach(client, coach_user, athlete_user, auth_headers_coach, db_session):
    """Tests coach retrieving notifications."""
    notif = Notification(
        id=uuid.uuid4(),
        recipient_id=coach_user.id,
        athlete_id=athlete_user.id,
        athlete_name=f"{athlete_user.first_name} {athlete_user.last_name}",
        session_id=str(uuid.uuid4()),
        risk_level="high",
        sport_type="BASKETBALL",
        message="High injury risk detected in basketball session.",
        is_read=False,
        created_at=datetime.utcnow(),
    )
    db_session.add(notif)
    db_session.commit()

    response = client.get("/api/notifications", headers=auth_headers_coach)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["risk_level"] == "high"


def test_dismiss_single_notification(client, coach_user, athlete_user, auth_headers_coach, db_session):
    """Tests dismissing an individual notification (deletes notification row)."""
    notif = Notification(
        id=uuid.uuid4(),
        recipient_id=coach_user.id,
        athlete_id=athlete_user.id,
        athlete_name=f"{athlete_user.first_name} {athlete_user.last_name}",
        session_id=str(uuid.uuid4()),
        risk_level="critical",
        message="Critical injury risk detected.",
        is_read=False,
    )
    db_session.add(notif)
    db_session.commit()

    response = client.delete(f"/api/notifications/{notif.id}", headers=auth_headers_coach)
    assert response.status_code in [200, 204]

    # Verify notification row was deleted from database
    found = db_session.query(Notification).filter(Notification.id == notif.id).first()
    assert found is None


def test_clear_all_notifications(client, coach_user, athlete_user, auth_headers_coach, db_session):
    """Tests clearing all notifications for a recipient."""
    for i in range(3):
        db_session.add(Notification(
            id=uuid.uuid4(),
            recipient_id=coach_user.id,
            athlete_id=athlete_user.id,
            athlete_name="Athlete",
            session_id=str(uuid.uuid4()),
            risk_level="high",
            message=f"Alert {i}",
            is_read=False,
        ))
    db_session.commit()

    response = client.delete("/api/notifications", headers=auth_headers_coach)
    assert response.status_code in [200, 204]

    remaining = db_session.query(Notification).filter(
        Notification.recipient_id == coach_user.id
    ).count()
    assert remaining == 0
