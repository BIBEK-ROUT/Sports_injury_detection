from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.routes.auth import get_current_user
from app.models.user import User
from app.models.athlete import AthleteProfile, InjuryHistory
from app.schemas.athlete import (
    AthleteProfileCreate,
    AthleteProfileResponse,
    AthleteLinkRequest,
    InjuryHistoryCreate,
    InjuryHistoryResponse,
)
from typing import List
import uuid
from datetime import datetime

router = APIRouter(prefix="/api/athletes", tags=["Athlete Profile"])


# ─── List All Athletes (coach / physio / scientist) ────────────────

@router.get("/all", summary="List all athletes on the platform")
def get_all_athletes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns all users with the 'athlete' role, including their latest risk level,
    overall symmetry, and session count. Accessible to coach, physiotherapist,
    sports_scientist, and admin roles only.
    """
    from app.models.video_analysis import VideoAnalysis

    allowed_roles = {"coach", "physiotherapist", "scientist", "admin"}
    if current_user.role.name not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail="Only coaches, physiotherapists, and sports scientists can view all athletes.",
        )

    # Get all users who have the athlete role (role_id = 1)
    query = db.query(User).join(User.role).filter(User.role.has(name="athlete"))

    # If the user is a coach or physio, only show their linked athletes
    if current_user.role.name == "coach":
        query = query.join(User.athlete_profile).filter(AthleteProfile.linked_coach_id == current_user.id)
    elif current_user.role.name == "physiotherapist":
        query = query.join(User.athlete_profile).filter(AthleteProfile.linked_physio_id == current_user.id)

    athletes = query.order_by(User.first_name).all()

    result = []
    for athlete in athletes:
        # Get their latest analysis
        latest = (
            db.query(VideoAnalysis)
            .filter(VideoAnalysis.user_id == str(athlete.id))
            .order_by(VideoAnalysis.created_at.desc())
            .first()
        )
        session_count = (
            db.query(VideoAnalysis)
            .filter(VideoAnalysis.user_id == str(athlete.id))
            .count()
        )
        profile = db.query(AthleteProfile).filter(
            AthleteProfile.user_id == str(athlete.id)
        ).first()

        result.append({
            "user_id":          str(athlete.id),
            "first_name":       athlete.first_name,
            "last_name":        athlete.last_name,
            "email":            athlete.email,
            "sport_type":       profile.sport_type if profile else None,
            "session_count":    session_count,
            "latest_risk":      latest.risk_level if latest else None,
            "latest_symmetry":  latest.avg_overall_symmetry if latest else None,
            "last_session_at":  latest.created_at.isoformat() if latest and latest.created_at else None,
        })

    return result




# ─── Get My Profile ────────────────────────────────────────────────

@router.get("/profile", response_model=AthleteProfileResponse)
def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the athlete profile for the currently logged-in user."""
    profile = db.query(AthleteProfile).filter(
        AthleteProfile.user_id == str(current_user.id)
    ).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete profile not found. Please create one first.",
        )

    # Attach professional user info if linked
    if profile.linked_coach_id:
        coach_user = db.query(User).filter(User.id == profile.linked_coach_id).first()
        if coach_user:
            profile.linked_coach = coach_user
    if profile.linked_physio_id:
        physio_user = db.query(User).filter(User.id == profile.linked_physio_id).first()
        if physio_user:
            profile.linked_physio = physio_user

    return profile


# ─── Create Profile ────────────────────────────────────────────────

@router.post("/profile", response_model=AthleteProfileResponse, status_code=status.HTTP_201_CREATED)
def create_profile(
    profile_data: AthleteProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create an athlete profile for the currently logged-in user."""
    # Check if profile already exists
    existing = db.query(AthleteProfile).filter(
        AthleteProfile.user_id == str(current_user.id)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile already exists. Use PUT to update it.",
        )

    profile = AthleteProfile(
        id=uuid.uuid4(),
        user_id=current_user.id,
        **profile_data.model_dump(),
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


# ─── Update Profile ────────────────────────────────────────────────

@router.put("/profile", response_model=AthleteProfileResponse)
def update_profile(
    profile_data: AthleteProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the athlete profile for the currently logged-in user."""
    profile = db.query(AthleteProfile).filter(
        AthleteProfile.user_id == str(current_user.id)
    ).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Please create one first.",
        )

    for field, value in profile_data.model_dump().items():
        setattr(profile, field, value)

    profile.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(profile)
    return profile


# ─── Link Professional (Athlete -> Coach / Physio) ─────────────────

@router.post("/link", response_model=dict)
def link_professional(
    request: AthleteLinkRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Link the current athlete to a coach or physiotherapist using an invite code."""
    if current_user.role.name != "athlete":
        raise HTTPException(status_code=403, detail="Only athletes can link to professionals.")

    profile = db.query(AthleteProfile).filter(AthleteProfile.user_id == str(current_user.id)).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Create your athlete profile first.")

    # Find professional by invite code
    professional = db.query(User).filter(User.invite_code == request.invite_code.strip().upper()).first()
    if not professional:
        raise HTTPException(status_code=404, detail="Invalid invite code.")

    role_title = professional.role.name.capitalize()
    pro_name = f"{professional.first_name} {professional.last_name}"
    athlete_name = f"{current_user.first_name} {current_user.last_name}"

    if professional.role.name == "coach":
        if profile.linked_coach_id:
            current_coach = db.query(User).filter(User.id == profile.linked_coach_id).first()
            coach_name = f"Coach {current_coach.first_name} {current_coach.last_name}" if current_coach else "another coach"
            raise HTTPException(
                status_code=400,
                detail=f"You are already linked to {coach_name}. Please unlink from your current coach first before connecting to a new one."
            )
        profile.linked_coach_id = professional.id
    elif professional.role.name == "physiotherapist":
        if profile.linked_physio_id:
            current_physio = db.query(User).filter(User.id == profile.linked_physio_id).first()
            physio_name = f"Physiotherapist {current_physio.first_name} {current_physio.last_name}" if current_physio else "another physiotherapist"
            raise HTTPException(
                status_code=400,
                detail=f"You are already linked to {physio_name}. Please unlink from your current physiotherapist first before connecting to a new one."
            )
        profile.linked_physio_id = professional.id
    else:
        raise HTTPException(status_code=400, detail="This code does not belong to a valid professional.")

    db.commit()

    # Log user_linked audit event
    from app.core.activity_logger import log_activity
    log_activity(
        event="user_linked",
        user_name=athlete_name,
        user_email=current_user.email,
        user_role="athlete",
        details=f"Athlete {athlete_name} linked to {role_title} {pro_name} ({professional.email})",
    )

    return {"status": "success", "message": f"Successfully linked to {role_title} {pro_name}!"}


# ─── Unlink Professional (Athlete self-removal) ────────────────────

@router.post("/unlink", response_model=dict)
def unlink_professional_self(
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Allows an athlete to unlink themselves from their coach or physiotherapist."""
    if current_user.role.name != "athlete":
        raise HTTPException(status_code=403, detail="Only athletes can use this endpoint.")

    profile = db.query(AthleteProfile).filter(AthleteProfile.user_id == str(current_user.id)).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Athlete profile not found.")

    pro_type = (request.get("professional_type") or "").strip().lower()
    athlete_name = f"{current_user.first_name} {current_user.last_name}"
    unlinked_from = ""

    from app.models.notification import Notification

    if pro_type in ["coach", "linked_coach"]:
        if profile.linked_coach_id:
            coach = db.query(User).filter(User.id == profile.linked_coach_id).first()
            unlinked_from = f"Coach {coach.first_name} {coach.last_name}" if coach else "Coach"
            # Purge previous pending notifications from this athlete to this coach
            db.query(Notification).filter(
                Notification.recipient_id == profile.linked_coach_id,
                Notification.athlete_id == current_user.id
            ).delete()
            # Send disconnection notification to coach
            coach_notif = Notification(
                recipient_id=profile.linked_coach_id,
                athlete_id=current_user.id,
                athlete_name=athlete_name,
                session_id=None,
                risk_level="unlinked",
                sport_type=profile.sport_type,
                message=f"Athlete {athlete_name} has unlinked from your coaching roster.",
            )
            db.add(coach_notif)
            profile.linked_coach_id = None
    elif pro_type in ["physiotherapist", "physio", "linked_physio"]:
        if profile.linked_physio_id:
            physio = db.query(User).filter(User.id == profile.linked_physio_id).first()
            unlinked_from = f"Physiotherapist {physio.first_name} {physio.last_name}" if physio else "Physiotherapist"
            # Purge previous pending notifications from this athlete to this physio
            db.query(Notification).filter(
                Notification.recipient_id == profile.linked_physio_id,
                Notification.athlete_id == current_user.id
            ).delete()
            # Send disconnection notification to physiotherapist
            physio_notif = Notification(
                recipient_id=profile.linked_physio_id,
                athlete_id=current_user.id,
                athlete_name=athlete_name,
                session_id=None,
                risk_level="unlinked",
                sport_type=profile.sport_type,
                message=f"Athlete {athlete_name} has unlinked from your physiotherapy roster.",
            )
            db.add(physio_notif)
            profile.linked_physio_id = None
    else:
        raise HTTPException(status_code=400, detail="Invalid professional type. Specify 'coach' or 'physiotherapist'.")

    db.commit()

    # Log user_unlinked audit event
    from app.core.activity_logger import log_activity
    log_activity(
        event="user_unlinked",
        user_name=athlete_name,
        user_email=current_user.email,
        user_role="athlete",
        details=f"Athlete {athlete_name} disconnected from {unlinked_from}",
    )

    return {"status": "success", "message": f"Successfully unlinked from {unlinked_from}."}


# ─── Remove Athlete from Roster (Coach / Physio removal) ───────────

@router.post("/{athlete_user_id}/unlink", response_model=dict)
def remove_athlete_from_roster(
    athlete_user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Allows a Coach or Physiotherapist to remove an athlete from their roster."""
    role_name = current_user.role.name if current_user.role else ""
    if role_name not in ["coach", "physiotherapist", "admin"]:
        raise HTTPException(status_code=403, detail="Only coaches, physiotherapists, or admins can remove athletes.")

    athlete_user = db.query(User).filter(User.id == athlete_user_id).first()
    if not athlete_user or not athlete_user.athlete_profile:
        raise HTTPException(status_code=404, detail="Athlete not found.")

    profile = athlete_user.athlete_profile
    pro_name = f"{current_user.first_name} {current_user.last_name}"
    athlete_name = f"{athlete_user.first_name} {athlete_user.last_name}"

    from app.models.notification import Notification
    # Purge any remaining notifications from this athlete to this professional
    db.query(Notification).filter(
        Notification.recipient_id == current_user.id,
        Notification.athlete_id == athlete_user_id
    ).delete()

    if role_name == "coach":
        if str(profile.linked_coach_id) != str(current_user.id):
            raise HTTPException(status_code=403, detail="Athlete is not linked to your coach account.")
        profile.linked_coach_id = None
    elif role_name == "physiotherapist":
        if str(profile.linked_physio_id) != str(current_user.id):
            raise HTTPException(status_code=403, detail="Athlete is not linked to your physiotherapist account.")
        profile.linked_physio_id = None
    elif role_name == "admin":
        profile.linked_coach_id = None
        profile.linked_physio_id = None

    db.commit()

    # Log user_unlinked audit event
    from app.core.activity_logger import log_activity
    log_activity(
        event="user_unlinked",
        user_name=pro_name,
        user_email=current_user.email,
        user_role=role_name,
        details=f"{role_name.capitalize()} {pro_name} removed Athlete {athlete_name} from their roster",
    )

    return {"status": "success", "message": f"Athlete {athlete_name} has been removed from your roster."}


# ─── Injury History ────────────────────────────────────────────────

@router.get("/injuries", response_model=List[InjuryHistoryResponse])
def get_injury_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all past injury records for the current user."""
    profile = db.query(AthleteProfile).filter(
        AthleteProfile.user_id == str(current_user.id)
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Athlete profile not found.")

    return profile.injury_histories


@router.post("/injuries", response_model=InjuryHistoryResponse, status_code=status.HTTP_201_CREATED)
def add_injury(
    injury_data: InjuryHistoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Log a new past injury record."""
    profile = db.query(AthleteProfile).filter(
        AthleteProfile.user_id == str(current_user.id)
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Athlete profile not found. Create a profile first.")

    injury = InjuryHistory(
        id=uuid.uuid4(),
        athlete_profile_id=profile.id,
        **injury_data.model_dump(),
    )
    db.add(injury)
    db.commit()
    db.refresh(injury)
    return injury


@router.get("/{user_id}/injuries", response_model=List[InjuryHistoryResponse])
def get_athlete_injuries(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the injury history for a specific athlete (for authorized professionals)."""
    allowed_roles = {"coach", "physiotherapist", "scientist", "admin"}
    if current_user.role.name not in allowed_roles:
        raise HTTPException(status_code=403, detail="Not authorized.")

    athlete = db.query(User).filter(User.id == user_id).first()
    if not athlete or not athlete.athlete_profile:
        raise HTTPException(status_code=404, detail="Athlete not found.")

    profile = athlete.athlete_profile
    if current_user.role.name == "coach" and profile.linked_coach_id != current_user.id:
        raise HTTPException(status_code=403, detail="Athlete not linked to you.")
    if current_user.role.name == "physiotherapist" and profile.linked_physio_id != current_user.id:
        raise HTTPException(status_code=403, detail="Athlete not linked to you.")

    return profile.injury_histories
