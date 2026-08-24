"""
Admin Routes — Secure endpoints for platform administrators only.

All routes in this file require a valid JWT token where the user's role
is exactly "admin". Any other role will receive a 403 Forbidden response.

Endpoints:
- GET  /api/public/config       — Public config (no auth) for frontend enforcement
- GET  /api/admin/stats         — Platform-wide statistics for the dashboard
- GET  /api/admin/users         — List all registered users
- PATCH /api/admin/users/{id}/status  — Activate or deactivate a user
- DELETE /api/admin/users/{id}  — Permanently delete a user and all their data
- GET  /api/admin/config        — Fetch all system configuration settings
- POST /api/admin/config        — Update a system configuration setting
- GET  /api/admin/activity      — All video analyses across all users (activity monitor)
"""

import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.api.routes.auth import get_current_user
from app.models.user import User, Role
from app.models.video_analysis import VideoAnalysis
from app.models.athlete import AthleteProfile
from app.models.system_config import SystemConfig, DEFAULT_CONFIGS

router = APIRouter(prefix="/api/admin", tags=["Admin"])


# ─── Admin Guard Dependency ─────────────────────────────────────────────────

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency that blocks anyone who is not an Admin from accessing admin routes."""
    if current_user.role.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Administrator privileges required."
        )
    return current_user


# ─── Pydantic Schemas ────────────────────────────────────────────────────────

class UserAdminView(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    role: str
    is_active: bool
    created_at: str

    class Config:
        from_attributes = True


class StatusUpdateRequest(BaseModel):
    is_active: bool
    reason: Optional[str] = None   # reason for deactivation (for future email service)


class ConfigUpdateRequest(BaseModel):
    key: str
    value: str


# ─── Helper: Seed Default Configs ───────────────────────────────────────────

def seed_default_configs(db: Session):
    """Insert default system config rows if they don't exist yet."""
    for cfg in DEFAULT_CONFIGS:
        existing = db.query(SystemConfig).filter(SystemConfig.key == cfg["key"]).first()
        if not existing:
            db.add(SystemConfig(**cfg))
    db.commit()


# ─── GET /api/admin/stats ────────────────────────────────────────────────────

@router.get("/stats")
def get_platform_stats(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin)
):
    """Returns global platform statistics for the Admin Overview dashboard."""

    # Total users grouped by role
    role_counts = (
        db.query(Role.name, func.count(User.id).label("count"))
        .join(User, User.role_id == Role.id)
        .group_by(Role.name)
        .all()
    )
    users_by_role = {row.name: row.count for row in role_counts}
    total_users = sum(users_by_role.values())

    # Total videos analyzed
    total_videos = db.query(func.count(VideoAnalysis.id)).scalar() or 0

    # Risk distribution across all analyzed videos
    risk_counts = (
        db.query(VideoAnalysis.risk_level, func.count(VideoAnalysis.id).label("count"))
        .filter(VideoAnalysis.risk_level.isnot(None))
        .group_by(VideoAnalysis.risk_level)
        .all()
    )
    risk_distribution = {row.risk_level: row.count for row in risk_counts}

    # Active vs Inactive users
    active_count = db.query(func.count(User.id)).filter(User.is_active == True).scalar() or 0
    inactive_count = db.query(func.count(User.id)).filter(User.is_active == False).scalar() or 0

    from app.core.ai_tracker import get_ai_usage_summary
    ai_telemetry = get_ai_usage_summary()

    return {
        "total_users": total_users,
        "users_by_role": users_by_role,
        "active_users": active_count,
        "inactive_users": inactive_count,
        "total_videos_analyzed": total_videos,
        "risk_distribution": risk_distribution,
        "ai_usage": ai_telemetry,
    }


# ─── GET /api/admin/users ────────────────────────────────────────────────────

@router.get("/users")
def get_all_users(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin)
):
    """Returns a list of every registered user on the platform."""
    users = db.query(User).join(Role).order_by(User.created_at.desc()).all()
    return [
        {
            "id": str(u.id),
            "email": u.email,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "role": u.role.name,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat(),
        }
        for u in users
    ]


# ─── PATCH /api/admin/users/{user_id}/status ────────────────────────────────

@router.patch("/users/{user_id}/status")
def update_user_status(
    user_id: str,
    body: StatusUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Activate or deactivate a user account. Admin cannot deactivate themselves."""
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")
    if str(target.id) == str(admin.id):
        raise HTTPException(status_code=400, detail="You cannot deactivate your own admin account.")

    target.is_active = body.is_active
    db.commit()

    action = "activated" if body.is_active else "deactivated"
    
    # Log status change audit event
    from app.core.activity_logger import log_activity
    log_activity(
        event="user_status_changed",
        user_name=f"{admin.first_name} {admin.last_name}",
        user_email=admin.email,
        user_role="admin",
        details=f"Admin {action} user {target.first_name} {target.last_name} ({target.email})",
    )

    return {"message": f"User {target.email} has been {action} successfully."}


# ─── DELETE /api/admin/users/{user_id} ──────────────────────────────────────

@router.delete("/users/{user_id}")
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Permanently delete a user account and all their associated data."""
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")
    if str(target.id) == str(admin.id):
        raise HTTPException(status_code=400, detail="You cannot delete your own admin account.")

    target_name = f"{target.first_name} {target.last_name}"
    target_email = target.email
    target_role = target.role.name if target.role else "unknown"

    # 1. Delete physical video files
    analyses = db.query(VideoAnalysis).filter(VideoAnalysis.user_id == str(target.id)).all()
    output_dir_base = Path("uploads/pose_outputs")
    for analysis in analyses:
        session_dir = output_dir_base / analysis.session_id
        if session_dir.exists() and session_dir.is_dir():
            shutil.rmtree(session_dir, ignore_errors=True)

    # 2. Delete database records
    db.query(VideoAnalysis).filter(VideoAnalysis.user_id == str(target.id)).delete()
    if target.athlete_profile:
        db.delete(target.athlete_profile)
    db.delete(target)
    db.commit()

    # Log user deletion audit event
    from app.core.activity_logger import log_activity
    log_activity(
        event="user_deleted",
        user_name=f"{admin.first_name} {admin.last_name}",
        user_email=admin.email,
        user_role="admin",
        details=f"Admin permanently deleted {target_name} ({target_email}, {target_role})",
    )

    return {"message": f"User {target_email} and all associated data have been permanently deleted."}


# ─── GET /api/admin/config ───────────────────────────────────────────────────

@router.get("/config")
def get_system_config(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin)
):
    """Fetch all system configuration settings. Seeds defaults if first time."""
    seed_default_configs(db)
    configs = db.query(SystemConfig).all()
    return [
        {
            "key": c.key,
            "value": c.value,
            "description": c.description,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }
        for c in configs
    ]


# ─── POST /api/admin/config ──────────────────────────────────────────────────

@router.post("/config")
def update_system_config(
    body: ConfigUpdateRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin)
):
    """Update a system configuration setting value."""
    config = db.query(SystemConfig).filter(SystemConfig.key == body.key).first()
    if not config:
        raise HTTPException(status_code=404, detail=f"Config key '{body.key}' not found.")
    config.value = body.value
    db.commit()
    return {"message": f"Config '{body.key}' updated to '{body.value}' successfully."}


# ─── GET /api/public/config (NO AUTH — used by frontend before login) ─────────

@router.get("/public/config", tags=["Public"])
def get_public_config(db: Session = Depends(get_db)):
    """
    Public endpoint — no authentication required.
    Returns only the settings needed for frontend enforcement:
    maintenance_mode, ai_chatbot_enabled, allow_new_registrations.
    """
    seed_default_configs(db)
    keys = ["maintenance_mode", "ai_chatbot_enabled", "allow_new_registrations"]
    configs = db.query(SystemConfig).filter(SystemConfig.key.in_(keys)).all()
    return {c.key: c.value for c in configs}


# ─── GET /api/admin/activity ──────────────────────────────────────────────────

@router.get("/activity")
def get_activity_monitor(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin)
):
    """
    Returns platform-wide audit trail:
    - Video uploads & risk scores
    - Session deletions
    - PDF Report exports across all roles
    - User registrations
    - Professional link & unlink events
    - Admin status updates & user deletions
    """
    from app.core.activity_logger import get_all_activity_events

    # ── Part 1: All logged audit events ───────────────────────────────────────
    logged_events = get_all_activity_events()
    logged_sessions = {e["session_id"] for e in logged_events if e["session_id"]}

    result = list(logged_events)

    # ── Part 2: Fill in historical DB analyses not already in memory ───────────
    analyses = (
        db.query(VideoAnalysis)
        .order_by(VideoAnalysis.created_at.desc())
        .limit(100)
        .all()
    )

    user_cache: dict = {}
    for a in analyses:
        sid = str(a.session_id)
        if sid in logged_sessions:
            continue
        uid = str(a.user_id) if a.user_id else None
        if uid and uid not in user_cache:
            user_cache[uid] = db.query(User).filter(User.id == a.user_id).first()
        u = user_cache.get(uid)
        result.append({
            "session_id":       sid,
            "event":            "video_uploaded",
            "user_name":        f"{u.first_name} {u.last_name}" if u else "Unknown Athlete",
            "user_email":       u.email if u else "—",
            "user_role":        u.role.name if u and u.role else "athlete",
            "details":          f"Analyzed {a.original_filename or 'video'} — Risk: {(a.risk_level or 'PENDING').upper()}",
            "filename":         a.original_filename or "video.mp4",
            "duration_seconds": a.duration_seconds,
            "risk_level":       a.risk_level or "pending",
            "created_at":       a.created_at.isoformat(),
        })

    # ── Sort all events newest first ──────────────────────────────────────────
    result.sort(key=lambda x: x["created_at"], reverse=True)
    return result[:250]


