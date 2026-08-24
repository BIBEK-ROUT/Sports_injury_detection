from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import (
    hash_password, verify_password, create_access_token, decode_access_token,
    create_password_reset_token, decode_password_reset_token
)
from app.models.user import User, Role
from app.models.system_config import SystemConfig
from app.schemas.user import (
    UserCreate, UserResponse, Token, ForgotPasswordRequest, ResetPasswordRequest
)
from app.core.email import send_smtp_email, get_reset_email_template
import secrets

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ─── Register ──────────────────────────────────────────────────

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user account."""

    # Check if new registrations are allowed by the Admin
    reg_config = db.query(SystemConfig).filter(SystemConfig.key == "allow_new_registrations").first()
    if reg_config and reg_config.value == "false":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="New account registrations are currently closed by the platform administrator. Please try again later."
        )

    # Check if email already exists
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists."
        )

    # Validate role exists
    role = db.query(Role).filter(Role.id == user_data.role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role selected."
        )

    # Block anyone from self-registering as Admin — admins are created via the backend script only
    if role.name == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator accounts cannot be created through this endpoint."
        )

    # Generate invite code for professionals
    invite_code = None
    if role.name in ["coach", "physiotherapist"]:
        # generate 6 char hex code e.g. 8A3F9B
        invite_code = secrets.token_hex(3).upper()

    # Create new user
    new_user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        role_id=user_data.role_id,
        invite_code=invite_code
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Log new user registration audit event
    from app.core.activity_logger import log_activity
    log_activity(
        event="user_registered",
        user_name=f"{new_user.first_name} {new_user.last_name}",
        user_email=new_user.email,
        user_role=role.name,
        details=f"New {role.name.capitalize()} account created",
    )

    return new_user


# ─── Login ─────────────────────────────────────────────────────

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login with email and password. Returns a JWT access token."""

    user = db.query(User).filter(User.email.ilike(form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated. Please contact support at sportguardsupport@gmail.com for assistance."
        )

    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


# ─── Get Current User ──────────────────────────────────────────

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Dependency: Decode JWT and return the current logged-in user."""
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return user


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Get the profile of the currently logged-in user."""
    return current_user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Delete the current user's account and all associated data.
    This includes their athlete profile, all video analyses, and saved physical files.
    """
    import shutil
    from pathlib import Path
    from app.models.athlete import AthleteProfile
    from app.models.video_analysis import VideoAnalysis
    
    # 1. Delete associated physical files (video analysis outputs)
    analyses = db.query(VideoAnalysis).filter(VideoAnalysis.user_id == str(current_user.id)).all()
    output_dir_base = Path("uploads/pose_outputs")
    for analysis in analyses:
        session_dir = output_dir_base / analysis.session_id
        if session_dir.exists() and session_dir.is_dir():
            shutil.rmtree(session_dir, ignore_errors=True)
    
    # 2. Delete DB records
    # Due to SQLAlchemy relationships without cascade="all, delete-orphan", 
    # we manually delete children to avoid foreign key constraint errors.
    db.query(VideoAnalysis).filter(VideoAnalysis.user_id == str(current_user.id)).delete()
    db.query(AthleteProfile).filter(AthleteProfile.user_id == str(current_user.id)).delete()
    
    # 3. Delete the user
    db.delete(current_user)
    db.commit()
    
    return None


# ─── Forgot Password ──────────────────────────────────────────

@router.post("/forgot-password", status_code=status.HTTP_200_OK)
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Step 1: Request password reset email.
    Generates a secure 15-minute token and emails it to the user.
    """
    user = db.query(User).filter(User.email.ilike(data.email)).first()
    if not user:
        # Standard security practice: do not leak whether an email exists or not.
        # Still return a success message.
        return {"message": "If this email is registered, a password reset link has been sent."}

    # Generate secure 15-min token
    token = create_password_reset_token(user.email, user.hashed_password)

    # Build reset URL (points to our React/Next.js frontend)
    # Typically this would read from configuration, but for local/demo we use localhost:3000
    reset_url = f"http://localhost:3000/reset-password?token={token}"

    # Prepare email content
    subject = "Reset Your SportGuard Password"
    html_content = get_reset_email_template(reset_url, user.first_name)
    text_content = (
        f"Hello {user.first_name},\n\n"
        "We received a request to reset the password for your SportGuard account. "
        f"Click the link below or copy it to your browser to set a new password:\n{reset_url}\n\n"
        "This link will expire in 15 minutes. If you did not make this request, you can safely ignore this email."
    )

    # Send email
    send_smtp_email(
        to_email=user.email,
        subject=subject,
        html_content=html_content,
        text_content=text_content
    )

    return {"message": "If this email is registered, a password reset link has been sent."}


# ─── Reset Password ───────────────────────────────────────────

@router.post("/reset-password", status_code=status.HTTP_200_OK)
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Step 2: Submit new password using the token.
    Decodes the token, checks signature against current password hash, and updates it.
    """
    payload = decode_password_reset_token(data.token)
    if not payload or not payload.get("sub") or not payload.get("pwh"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The password reset link is invalid or has expired. Please request a new one."
        )

    email = payload.get("sub")
    pwh_token = payload.get("pwh")

    # Fetch user
    user = db.query(User).filter(User.email.ilike(email)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The password reset link is invalid or has expired."
        )

    # Check if the token has already been used.
    # The token payload contains the last 10 characters of the hashed_password.
    # If the user has already reset their password, the current hash will be different,
    # and this check will fail, preventing reuse of the same link!
    if user.hashed_password[-10:] != pwh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password reset link has already been used. Please request a new one."
        )

    # Hash and update new password
    user.hashed_password = hash_password(data.new_password)
    db.commit()

    return {"message": "Your password has been successfully reset. You can now login with your new password."}
