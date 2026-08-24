"""
Video Router — FastAPI endpoints for video upload and pose analysis.

This is the thin HTTP wrapper. It:
1. Receives a video file from the React frontend via HTTP POST
2. Saves it to a temporary location on the server
3. Calls the SAME service.process_video() that the local demo also calls
4. Saves the results to the database linked to the current user
5. Returns a structured JSON response with results and image URLs

When deployed, this is ALL that changes from the local demo:
- Input: HTTP file upload instead of a file picker
- Output: JSON response instead of an OpenCV window
- Core AI logic: IDENTICAL (service.process_video is unchanged)
"""

import os
import json
import uuid
import shutil
import logging
from pathlib import Path
from datetime import datetime, date

logger = logging.getLogger(__name__)

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.routes.auth import get_current_user
from app.models.user import User
from app.models.video_analysis import VideoAnalysis
from app.models.athlete import AthleteProfile
from app.models.notification import Notification
from app.ml.pose_estimation.service import process_video, VideoAnalysisResult
from app.ml.inference import predict_injury_risk
from app.ml.ai_service import generate_static_recommendation
from app.services.pdf_service import generate_athlete_report_pdf

router = APIRouter(prefix="/api/video", tags=["Video Analysis"])

# Directories on the server where files are stored
UPLOAD_DIR = Path("uploads/videos")
OUTPUT_DIR = Path("uploads/pose_outputs")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Allowed video formats
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


def _save_ai_recs_in_background(
    session_id: str,
    risk_level: str,
    sport_type: str,
    active_flags: dict,
) -> None:
    """
    Called as a FastAPI BackgroundTask after the HTTP response is already sent.
    Calls Gemini, then writes ai_recommendations back to the DB record.
    Running this in the background cuts the user-facing response time
    from ~20 seconds down to ~8 seconds.
    """
    from app.core.database import SessionLocal  # local import to avoid circular dep
    from app.models.athlete import AthleteProfile
    from app.models.video_analysis import VideoAnalysis
    
    db = SessionLocal()
    try:
        # Fetch the session and the user's injury history
        analysis = db.query(VideoAnalysis).filter(VideoAnalysis.session_id == session_id).first()
        injury_history = []
        if analysis:
            profile = db.query(AthleteProfile).filter(AthleteProfile.user_id == analysis.user_id).first()
            if profile and profile.injury_histories:
                injury_history = [f"{inj.injury_name} ({inj.affected_body_part})" for inj in profile.injury_histories]

        ai_recs = generate_static_recommendation(
            risk_level=risk_level,
            sport_type=sport_type,
            active_flags=active_flags,
            injury_history=injury_history,
        )
        if not ai_recs:
            ai_recs = {
                "exercise_recommendations": ["(AI generation temporarily unavailable)"],
                "mobility_suggestions": ["(Please consult your coach for alternatives)"],
                "recovery_planning": ["(Ensure adequate rest and hydration)"]
            }
        
        if analysis:
            analysis.ai_recommendations = json.dumps(ai_recs)
            db.commit()
            logger.info(f"AI recommendations saved in background for session {session_id}")
    except Exception as e:
        logger.warning(f"Background AI recommendation failed for session {session_id}: {e}")
        try:
            if analysis:
                fallback = {
                    "exercise_recommendations": ["(AI generation failed)"],
                    "mobility_suggestions": ["(Please consult your coach)"],
                    "recovery_planning": ["(Ensure adequate rest)"]
                }
                analysis.ai_recommendations = json.dumps(fallback)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()



@router.post("/analyze", summary="Upload a video and run pose estimation + biomechanics")
async def analyze_video(
    file: UploadFile = File(..., description="Video file to analyze"),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Upload a video and get full pose estimation + biomechanical analysis results.
    Results are saved to the database linked to the authenticated user.

    - Accepts: MP4, MOV, AVI, MKV, WEBM
    - Returns: JSON with detection stats, biomechanics metrics, risk flags, and image URLs
    """
    # ── Daily quota check (5 videos per user per day) ──────────────────────
    today_start = datetime.combine(date.today(), datetime.min.time())
    videos_today = db.query(VideoAnalysis).filter(
        VideoAnalysis.user_id == str(current_user.id),
        VideoAnalysis.created_at >= today_start,
    ).count()
    DAILY_VIDEO_LIMIT = 5
    if videos_today >= DAILY_VIDEO_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Daily video analysis limit reached ({videos_today}/{DAILY_VIDEO_LIMIT}). "
                   f"Please try again tomorrow to ensure fair platform usage for all users."
        )

    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Generate a unique session ID for this analysis
    session_id = str(uuid.uuid4())

    # Save the uploaded video to disk
    video_path = UPLOAD_DIR / f"{session_id}{file_ext}"
    try:
        with open(video_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    # Create a session-specific output folder for annotated frames
    session_output_dir = OUTPUT_DIR / session_id
    session_output_dir.mkdir(parents=True, exist_ok=True)

    # ── Call the SAME service function the local demo uses ──────────
    try:
        result: VideoAnalysisResult = process_video(
            video_path=str(video_path),
            output_dir=str(session_output_dir),
        )
    except Exception as e:
        # Clean up the uploaded video even if analysis fails
        video_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    # Delete the original uploaded video after processing
    video_path.unlink(missing_ok=True)

    # Build URL paths for the saved annotated images and the skeleton video
    image_urls = [
        f"/uploads/pose_outputs/{session_id}/{Path(p).name}"
        for p in result.saved_image_paths
    ]
    annotated_video_url = (
        f"/uploads/pose_outputs/{session_id}/{Path(result.annotated_video_path).name}"
        if result.annotated_video_path and Path(result.annotated_video_path).exists()
        else None
    )

    # ── Fetch athlete sport type from AthleteProfile ─────────────────
    # XGBoost uses the sport to apply sport-specific risk thresholds.
    athlete_profile = (
        db.query(AthleteProfile)
        .filter(AthleteProfile.user_id == str(current_user.id))
        .first()
    )
    sport_type = athlete_profile.sport_type if athlete_profile else "OTHER"

    # ── Run XGBoost Inference ─────────────────────────────────────────
    # Use PERCENTAGE thresholds, not "any single frame".
    # One blurry/transitional frame must NOT trigger a permanent HIGH risk label.
    _pose_frames = max(result.frames_with_pose, 1)  # avoid division by zero

    # Hyperextension: serious structural risk -> flag if >10% of frames show it
    flag_knee_hyperext = 1 if (result.frames_knee_hyperextension / _pose_frames) > 0.10 else 0
    # Knee valgus (inward collapse): flag if >15% of frames show it
    flag_knee_valgus   = 1 if (result.frames_knee_valgus / _pose_frames) > 0.15 else 0
    # Trunk lean: flag if >20% of frames show sustained excessive lean
    flag_trunk_lean    = 1 if (result.frames_excessive_trunk_lean / _pose_frames) > 0.20 else 0
    # Low symmetry: flag if >25% of frames (dynamic movement is naturally asymmetric)
    flag_low_symmetry  = 1 if (result.frames_low_symmetry / _pose_frames) > 0.25 else 0

    prediction = predict_injury_risk(
        sport_type=sport_type,
        knee_flexion=(
            ((result.avg_left_knee_angle or 0) + (result.avg_right_knee_angle or 0)) / 2
            if result.avg_left_knee_angle or result.avg_right_knee_angle else None
        ),
        hip_angle=(
            ((result.avg_left_hip_angle or 0) + (result.avg_right_hip_angle or 0)) / 2
            if result.avg_left_hip_angle or result.avg_right_hip_angle else None
        ),
        elbow_angle=(
            ((result.avg_left_elbow_angle or 0) + (result.avg_right_elbow_angle or 0)) / 2
            if result.avg_left_elbow_angle or result.avg_right_elbow_angle else None
        ),
        shoulder_rotation=result.avg_shoulder_rotation,
        trunk_lean=result.avg_trunk_lean,
        knee_valgus_angle=result.avg_knee_valgus_angle,
        symmetry=result.avg_overall_symmetry,
        flag_knee_hyperext=flag_knee_hyperext,
        flag_knee_valgus=flag_knee_valgus,
        flag_trunk_lean=flag_trunk_lean,
        flag_low_symmetry=flag_low_symmetry,
    )

    risk_level = prediction.risk_level

    # ── Save results to DB immediately (WITHOUT waiting for Gemini) ─────
    # Gemini runs as a BackgroundTask AFTER the response is sent.
    # This cuts user-facing wait time from ~20s → ~8s.
    analysis = VideoAnalysis(
        user_id=str(current_user.id),
        session_id=session_id,
        original_filename=file.filename,
        duration_seconds=result.duration_seconds,
        total_frames=result.total_frames,
        frames_analyzed=result.frames_processed,
        frames_with_pose=result.frames_with_pose,
        pose_detection_rate=result.pose_detection_rate,
        annotated_frame_urls=json.dumps(image_urls),
        avg_left_knee_angle=result.avg_left_knee_angle,
        avg_right_knee_angle=result.avg_right_knee_angle,
        min_left_knee_angle=result.min_left_knee_angle,
        min_right_knee_angle=result.min_right_knee_angle,
        avg_left_hip_angle=result.avg_left_hip_angle,
        avg_right_hip_angle=result.avg_right_hip_angle,
        avg_left_elbow_angle=result.avg_left_elbow_angle,
        avg_right_elbow_angle=result.avg_right_elbow_angle,
        avg_trunk_lean=result.avg_trunk_lean,
        avg_knee_symmetry=result.avg_knee_symmetry,
        avg_hip_symmetry=result.avg_hip_symmetry,
        avg_overall_symmetry=result.avg_overall_symmetry,
        avg_knee_valgus_angle=result.avg_knee_valgus_angle,
        avg_shoulder_rotation=result.avg_shoulder_rotation,
        frames_knee_hyperextension=result.frames_knee_hyperextension,
        frames_knee_acute_flexion=result.frames_knee_acute_flexion,
        frames_excessive_trunk_lean=result.frames_excessive_trunk_lean,
        frames_low_symmetry=result.frames_low_symmetry,
        frames_elbow_hyperextension=result.frames_elbow_hyperextension,
        frames_knee_valgus=result.frames_knee_valgus,
        risk_level=risk_level,
        xgboost_confidence=prediction.confidence,
        xgboost_probabilities=json.dumps(prediction.probabilities),
        sport_type_used=prediction.sport_type,
        ai_recommendations=None,  # Will be filled by background task
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    # ── Log Video Upload Activity ──────────────────────────────────────
    from app.core.activity_logger import log_activity
    log_activity(
        event="video_uploaded",
        user_name=f"{current_user.first_name} {current_user.last_name}",
        user_email=current_user.email,
        user_role=current_user.role.name if current_user.role else "athlete",
        details=f"Analyzed {file.filename} ({sport_type}) — Risk: {risk_level.upper()}",
        filename=file.filename,
        session_id=session_id,
        risk_level=risk_level.lower(),
        duration_seconds=result.duration_seconds,
    )

    # ── Notification Alert Trigger for High / Critical Risk ────────────
    if risk_level.lower() in ["high", "critical"]:
        try:
            profile = db.query(AthleteProfile).filter(AthleteProfile.user_id == current_user.id).first()
            if profile:
                athlete_full_name = f"{current_user.first_name} {current_user.last_name}"
                recipients = []
                if profile.linked_coach_id:
                    recipients.append(profile.linked_coach_id)
                if profile.linked_physio_id:
                    recipients.append(profile.linked_physio_id)

                for r_id in set(recipients):
                    notif = Notification(
                        recipient_id=r_id,
                        athlete_id=current_user.id,
                        athlete_name=athlete_full_name,
                        session_id=session_id,
                        risk_level=risk_level.lower(),
                        sport_type=sport_type,
                        message=f"{athlete_full_name} was flagged with {risk_level.upper()} injury risk in their latest {sport_type} analysis.",
                    )
                    db.add(notif)
                if recipients:
                    db.commit()
                    logger.info(f"Created high-risk notifications for session {session_id} to recipients: {recipients}")
        except Exception as e:
            logger.warning(f"Failed to generate notifications for session {session_id}: {e}")

    # ── Schedule Gemini as background task (runs AFTER response is sent) ──
    if background_tasks is not None:
        background_tasks.add_task(
            _save_ai_recs_in_background,
            session_id=session_id,
            risk_level=risk_level,
            sport_type=sport_type,
            active_flags={
                "knee_hyperextension": flag_knee_hyperext == 1,
                "knee_valgus":          flag_knee_valgus == 1,
                "excessive_trunk_lean": flag_trunk_lean == 1,
                "low_symmetry":         flag_low_symmetry == 1,
                "knee_acute_flexion":   result.frames_knee_acute_flexion > 0,
                "elbow_hyperextension": result.frames_elbow_hyperextension > 0,
            },
        )

    return {
        "session_id": session_id,
        "risk_level": risk_level,

        # AI corrective plan — generated in background, available when revisiting session history
        "ai_recommendations": None,  # Gemini runs after response; reload session history to see it

        # XGBoost prediction details
        "xgboost": {
            "risk_level":     prediction.risk_level,
            "risk_score":     prediction.risk_score,
            "confidence":     prediction.confidence,
            "probabilities":  prediction.probabilities,
            "sport_used":     prediction.sport_type,
            "model_version":  prediction.model_version,
        },

        # Video metadata
        "video": {
            "filename": file.filename,
            "duration_seconds": result.duration_seconds,
            "total_frames": result.total_frames,
            "frames_analyzed": result.frames_processed,
            "frames_with_pose": result.frames_with_pose,
            "pose_detection_rate": result.pose_detection_rate,
        },

        # Skeleton video (temporary)
        "annotated_video_url": annotated_video_url,

        # Annotated frame screenshots (permanent)
        "annotated_frames": image_urls,

        # Full biomechanics
        "biomechanics": {
            "avg_left_knee_angle":   result.avg_left_knee_angle,
            "avg_right_knee_angle":  result.avg_right_knee_angle,
            "min_left_knee_angle":   result.min_left_knee_angle,
            "min_right_knee_angle":  result.min_right_knee_angle,
            "avg_left_hip_angle":    result.avg_left_hip_angle,
            "avg_right_hip_angle":   result.avg_right_hip_angle,
            "avg_left_elbow_angle":  result.avg_left_elbow_angle,
            "avg_right_elbow_angle": result.avg_right_elbow_angle,
            "avg_trunk_lean":        result.avg_trunk_lean,
            "avg_knee_symmetry":     result.avg_knee_symmetry,
            "avg_hip_symmetry":      result.avg_hip_symmetry,
            "avg_overall_symmetry":  result.avg_overall_symmetry,
            "avg_knee_valgus_angle": result.avg_knee_valgus_angle,
            "avg_shoulder_rotation": result.avg_shoulder_rotation,
        },

        # Risk flag counts (raw counts — shown to coaches and physiotherapists)
        "risk_flags": {
            "knee_hyperextension_frames":  result.frames_knee_hyperextension,
            "knee_acute_flexion_frames":   result.frames_knee_acute_flexion,
            "excessive_trunk_lean_frames": result.frames_excessive_trunk_lean,
            "low_symmetry_frames":         result.frames_low_symmetry,
            "elbow_hyperextension_frames": result.frames_elbow_hyperextension,
            "knee_valgus_frames":          result.frames_knee_valgus,
        },
    }


@router.get("/history", summary="Get all video analysis sessions for the current user")
def get_analysis_history(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return the list of all past video analysis sessions for the authenticated user."""
    analyses = (
        db.query(VideoAnalysis)
        .filter(VideoAnalysis.user_id == str(current_user.id))
        .order_by(VideoAnalysis.created_at.desc())
        .all()
    )
    return [
        {
            "session_id":          a.session_id,
            "filename":            a.original_filename,
            "duration_seconds":    a.duration_seconds,
            "pose_detection_rate": a.pose_detection_rate,
            "frames_analyzed":     a.frames_analyzed,
            "frames_with_pose":    a.frames_with_pose,
            "risk_level":          a.risk_level,
            "created_at":          a.created_at.isoformat() if a.created_at else None,
            "annotated_frames":    json.loads(a.annotated_frame_urls) if a.annotated_frame_urls else [],
            # XGBoost output
            "xgboost_confidence":    a.xgboost_confidence,
            "xgboost_probabilities": json.loads(a.xgboost_probabilities) if a.xgboost_probabilities else None,
            "sport_type_used":       a.sport_type_used,
            # AI Recommendations
            "ai_recommendations":     json.loads(a.ai_recommendations) if a.ai_recommendations else None,
            # Biomechanics
            "avg_left_knee_angle":   a.avg_left_knee_angle,
            "avg_right_knee_angle":  a.avg_right_knee_angle,
            "min_left_knee_angle":   a.min_left_knee_angle,
            "min_right_knee_angle":  a.min_right_knee_angle,
            "avg_left_hip_angle":    a.avg_left_hip_angle,
            "avg_right_hip_angle":   a.avg_right_hip_angle,
            "avg_left_elbow_angle":  a.avg_left_elbow_angle,
            "avg_right_elbow_angle": a.avg_right_elbow_angle,
            "avg_trunk_lean":        a.avg_trunk_lean,
            "avg_knee_symmetry":     a.avg_knee_symmetry,
            "avg_hip_symmetry":      a.avg_hip_symmetry,
            "avg_overall_symmetry":  a.avg_overall_symmetry,
            "avg_knee_valgus_angle": a.avg_knee_valgus_angle,
            "avg_shoulder_rotation": a.avg_shoulder_rotation,
            # Risk Flags
            "frames_knee_hyperextension":  a.frames_knee_hyperextension,
            "frames_knee_acute_flexion":   a.frames_knee_acute_flexion,
            "frames_excessive_trunk_lean": a.frames_excessive_trunk_lean,
            "frames_low_symmetry":         a.frames_low_symmetry,
            "frames_elbow_hyperextension": a.frames_elbow_hyperextension,
            "frames_knee_valgus":          a.frames_knee_valgus,
        }
        for a in analyses
    ]


@router.get("/athlete/{user_id}/history", summary="Get full analysis history for a specific athlete")
def get_athlete_history(
    user_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Returns the full analysis history for a given athlete user_id.
    Accessible by coach, physiotherapist, and sports_scientist roles.
    """
    from app.models.user import User
    allowed_roles = {"coach", "physiotherapist", "scientist", "admin"}
    if current_user.role.name not in allowed_roles:
        raise HTTPException(status_code=403, detail="Not authorised to view other users' data.")

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Athlete not found.")

    # Enforce linkage check for coaches and physiotherapists
    if current_user.role.name == "coach":
        if not target.athlete_profile or str(target.athlete_profile.linked_coach_id) != str(current_user.id):
            raise HTTPException(status_code=403, detail="You are no longer linked to this athlete.")
    elif current_user.role.name == "physiotherapist":
        if not target.athlete_profile or str(target.athlete_profile.linked_physio_id) != str(current_user.id):
            raise HTTPException(status_code=403, detail="You are no longer linked to this athlete.")

    analyses = (
        db.query(VideoAnalysis)
        .filter(VideoAnalysis.user_id == user_id)
        .order_by(VideoAnalysis.created_at.desc())
        .all()
    )
    return [
        {
            "session_id":           a.session_id,
            "filename":             a.original_filename,
            "duration_seconds":     a.duration_seconds,
            "pose_detection_rate":  a.pose_detection_rate,
            "frames_analyzed":      a.frames_analyzed,
            "frames_with_pose":     a.frames_with_pose,
            "risk_level":           a.risk_level,
            "created_at":           a.created_at.isoformat() if a.created_at else None,
            "annotated_frames":     json.loads(a.annotated_frame_urls) if a.annotated_frame_urls else [],
            # XGBoost output
            "xgboost_confidence":    a.xgboost_confidence,
            "xgboost_probabilities": json.loads(a.xgboost_probabilities) if a.xgboost_probabilities else None,
            "sport_type_used":       a.sport_type_used,
            # AI Recommendations
            "ai_recommendations":     json.loads(a.ai_recommendations) if a.ai_recommendations else None,
            # Biomechanics
            "avg_left_knee_angle":   a.avg_left_knee_angle,
            "avg_right_knee_angle":  a.avg_right_knee_angle,
            "min_left_knee_angle":   a.min_left_knee_angle,
            "min_right_knee_angle":  a.min_right_knee_angle,
            "avg_left_hip_angle":    a.avg_left_hip_angle,
            "avg_right_hip_angle":   a.avg_right_hip_angle,
            "avg_left_elbow_angle":  a.avg_left_elbow_angle,
            "avg_right_elbow_angle": a.avg_right_elbow_angle,
            "avg_trunk_lean":        a.avg_trunk_lean,
            "avg_knee_symmetry":     a.avg_knee_symmetry,
            "avg_hip_symmetry":      a.avg_hip_symmetry,
            "avg_overall_symmetry":  a.avg_overall_symmetry,
            "avg_knee_valgus_angle": a.avg_knee_valgus_angle,
            "avg_shoulder_rotation": a.avg_shoulder_rotation,
            # Risk Flags
            "frames_knee_hyperextension":  a.frames_knee_hyperextension,
            "frames_knee_acute_flexion":   a.frames_knee_acute_flexion,
            "frames_excessive_trunk_lean": a.frames_excessive_trunk_lean,
            "frames_low_symmetry":         a.frames_low_symmetry,
            "frames_elbow_hyperextension": a.frames_elbow_hyperextension,
            "frames_knee_valgus":          a.frames_knee_valgus,
        }
        for a in analyses
    ]




@router.delete(
    "/{session_id}/skeleton-video",
    summary="Delete the temporary skeleton video for a session",
    status_code=204,
)
def delete_skeleton_video(
    session_id: str,
    current_user=Depends(get_current_user),
):
    """
    Called by the frontend when the user is done watching the skeleton video
    (e.g. clicks 'New Video'). Deletes the MP4 to reclaim disk space.
    The annotated frame screenshots are NOT touched — they remain permanently.
    """
    # Security: only delete files inside our known output directory
    session_dir = OUTPUT_DIR / session_id
    video_file  = session_dir / f"{session_id}_skeleton.mp4"

    if video_file.exists():
        video_file.unlink()

    # Return 204 No Content whether the file existed or not
    return


# ── In-memory deletion event log (shown in Admin Activity Monitor) ────────────
# Each entry: {user_name, user_email, user_role, filename, deleted_at}
_deletion_log: list = []

def get_deletion_log() -> list:
    """Returns the most recent 100 deletion events."""
    return _deletion_log[-100:]


@router.delete(
    "/{session_id}",
    summary="Permanently delete an analysis record",
    status_code=200,
)
def delete_analysis(
    session_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Allows an athlete to permanently delete one of their own analysis records.
    - Only the owner of the record can delete it (ownership enforced).
    - Removes the DB row, all uploaded video files, and pose output files.
    - Logs a deletion event to the in-memory activity log for the Admin Monitor.
    """
    # Fetch the analysis record
    analysis = db.query(VideoAnalysis).filter(
        VideoAnalysis.session_id == session_id
    ).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis record not found.")

    # Ownership check — only the owner can delete their record
    if str(analysis.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=403,
            detail="You can only delete your own analysis records."
        )

    filename = analysis.original_filename or "unknown"

    # ── Log the deletion for the Admin Activity Monitor ────────────────────────
    from app.core.activity_logger import log_activity
    log_activity(
        event="video_deleted",
        user_name=f"{current_user.first_name} {current_user.last_name}",
        user_email=current_user.email,
        user_role=current_user.role.name if current_user.role else "unknown",
        details=f"Permanently deleted session for {filename}",
        filename=filename,
        session_id=session_id,
    )

    # ── Delete files from disk ─────────────────────────────────────────────────
    # 1. Uploaded source video
    for ext in ALLOWED_EXTENSIONS:
        candidate = UPLOAD_DIR / f"{session_id}{ext}"
        if candidate.exists():
            candidate.unlink()

    # 2. Pose output folder (skeleton video + annotated frame images)
    session_out_dir = OUTPUT_DIR / session_id
    if session_out_dir.exists():
        shutil.rmtree(session_out_dir, ignore_errors=True)

    # ── Delete the DB record ───────────────────────────────────────────────────
    db.delete(analysis)
    db.commit()

    return {"message": f"Analysis '{filename}' has been permanently deleted."}


# ─── PDF Report Export Endpoint ─────────────────────────────────────────────

@router.get(
    "/{session_id}/report/pdf",
    summary="Download 2-Page Clinical & Biomechanical PDF Assessment Report",
)
def download_pdf_report(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generates and streams a 2-page Clinical & Biomechanical Assessment PDF Report.
    Permissions:
    - Athlete: Can download for their own sessions.
    - Coach / Physio: Can download for athletes linked to them.
    - Scientist / Admin: Can download for any session.
    """
    analysis = db.query(VideoAnalysis).filter(VideoAnalysis.session_id == session_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis session not found.")

    athlete_user = db.query(User).filter(User.id == analysis.user_id).first()
    if not athlete_user:
        raise HTTPException(status_code=404, detail="Athlete user not found.")

    role_name = current_user.role.name if current_user.role else "athlete"

    # RBAC Check
    if role_name == "athlete" and str(current_user.id) != str(analysis.user_id):
        raise HTTPException(status_code=403, detail="You can only export reports for your own sessions.")
    elif role_name in ["coach", "physiotherapist"]:
        # Verify athlete is linked to this coach or physio
        profile = db.query(AthleteProfile).filter(AthleteProfile.user_id == analysis.user_id).first()
        if not profile or (str(profile.linked_coach_id) != str(current_user.id) and str(profile.linked_physio_id) != str(current_user.id)):
            raise HTTPException(status_code=403, detail="You do not have access to this athlete's report.")

    # Fetch athlete profile (for physical stats and past injury history)
    athlete_profile = db.query(AthleteProfile).filter(AthleteProfile.user_id == analysis.user_id).first()

    # Fetch historical sessions up to and including THIS session for progression trend
    history_records = (
        db.query(VideoAnalysis)
        .filter(
            VideoAnalysis.user_id == analysis.user_id,
            VideoAnalysis.created_at <= analysis.created_at
        )
        .order_by(VideoAnalysis.created_at.asc())
        .all()
    )

    # Log PDF report export event
    from app.core.activity_logger import log_activity
    viewer_title = role_name.capitalize()
    athlete_full_name = f"{athlete_user.first_name} {athlete_user.last_name}"
    log_activity(
        event="report_exported",
        user_name=f"{current_user.first_name} {current_user.last_name}",
        user_email=current_user.email,
        user_role=role_name,
        details=f"{viewer_title} exported 2-page PDF report for {athlete_full_name}",
        filename=analysis.original_filename or f"Report_{session_id[:8]}",
        session_id=session_id,
        risk_level=analysis.risk_level,
    )

    pdf_buffer = generate_athlete_report_pdf(
        analysis=analysis,
        athlete_user=athlete_user,
        athlete_profile=athlete_profile,
        history_records=history_records,
    )

    filename = f"SportGuard_Report_{athlete_user.last_name or 'Athlete'}_{session_id[:8]}.pdf"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=\"{filename}\"",
            "Cache-Control": "no-cache",
        }
    )
