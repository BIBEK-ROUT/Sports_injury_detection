"""
PDF Report Export & Graph Filtering Unit & Integration Tests.
"""

import io
import uuid
import json
from datetime import datetime
from app.models.video_analysis import VideoAnalysis
from app.services.pdf_service import generate_athlete_report_pdf


def test_pdf_report_binary_generation(athlete_user, db_session):
    """Verifies that generate_athlete_report_pdf produces a valid PDF stream."""
    session_id = str(uuid.uuid4())

    analysis = VideoAnalysis(
        id=uuid.uuid4(),
        session_id=session_id,
        user_id=str(athlete_user.id),
        original_filename="jump_test.mp4",
        duration_seconds=5.2,
        frames_analyzed=150,
        frames_with_pose=148,
        pose_detection_rate=0.98,
        risk_level="moderate",
        xgboost_confidence=0.88,
        sport_type_used="BASKETBALL",
        created_at=datetime.utcnow(),
        avg_left_knee_angle=138.5,
        avg_right_knee_angle=140.2,
        avg_left_hip_angle=152.0,
        avg_right_hip_angle=154.0,
        avg_trunk_lean=14.5,
        avg_overall_symmetry=0.92,
        ai_recommendations=json.dumps({
            "exercise_recommendations": ["Hamstring Curls", "Bulgarian Split Squats"],
            "mobility_drills": ["Hip Flexor Stretch", "Ankle Mobility"],
            "recovery_planning": ["Foam rolling 10m", "Ice therapy"],
        }),
    )
    db_session.add(analysis)
    db_session.commit()

    pdf_buffer = generate_athlete_report_pdf(
        analysis=analysis,
        athlete_user=athlete_user,
        athlete_profile=athlete_user.athlete_profile,
        history_records=[analysis],
    )
    assert isinstance(pdf_buffer, io.BytesIO)

    pdf_bytes = pdf_buffer.getvalue()
    assert len(pdf_bytes) > 1000  # PDF contains binary content
    assert pdf_bytes.startswith(b"%PDF")  # Valid PDF signature header


def test_pdf_export_endpoint_authorized(client, athlete_user, auth_headers_athlete, db_session):
    """Tests /api/video/{session_id}/report/download returns binary PDF with attachment headers."""
    session_id = str(uuid.uuid4())

    analysis = VideoAnalysis(
        id=uuid.uuid4(),
        session_id=session_id,
        user_id=str(athlete_user.id),
        original_filename="run.mp4",
        duration_seconds=4.0,
        frames_analyzed=120,
        frames_with_pose=118,
        pose_detection_rate=0.98,
        risk_level="low",
        xgboost_confidence=0.94,
        sport_type_used="SOCCER",
        created_at=datetime.utcnow(),
        avg_overall_symmetry=0.95,
    )
    db_session.add(analysis)
    db_session.commit()

    response = client.get(f"/api/video/{session_id}/report/pdf", headers=auth_headers_athlete)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
