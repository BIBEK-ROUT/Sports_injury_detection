from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi import APIRouter
from pathlib import Path
from app.core.database import engine, Base, get_db
from app.api.routes import auth, athletes, video, chat, admin, notifications
from app.models.system_config import SystemConfig
from sqlalchemy.orm import Session
from fastapi import Depends

# Import all models so SQLAlchemy can create their tables
from app.models import user, athlete, video_analysis, system_config, notification  # noqa: F401

# Create all database tables on startup
Base.metadata.create_all(bind=engine)

# ─── App Initialization ────────────────────────────────────────
app = FastAPI(
    title="Sports Injury Risk Detection API",
    description="AI-powered platform for detecting sports injury risks from movement videos.",
    version="1.0.0",
)

# ─── CORS Middleware ───────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Static Files (annotated pose images served to frontend) ───
uploads_path = Path("uploads")
uploads_path.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# ─── Routers ───────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(athletes.router)
app.include_router(video.router)
app.include_router(chat.router)
app.include_router(admin.router)
app.include_router(notifications.router)


# ─── Public Config (no auth needed) ─────────────────────────────────
public_router = APIRouter(prefix="/api/public", tags=["Public"])

@public_router.get("/config")
def get_public_config(db: Session = Depends(get_db)):
    """
    Public endpoint — no authentication required.
    Returns maintenance_mode, ai_chatbot_enabled, allow_new_registrations.
    Used by the frontend to enforce system config before and after login.
    """
    from app.models.system_config import DEFAULT_CONFIGS
    # Seed defaults on first call
    for cfg in DEFAULT_CONFIGS:
        existing = db.query(SystemConfig).filter(SystemConfig.key == cfg["key"]).first()
        if not existing:
            db.add(SystemConfig(**cfg))
    db.commit()
    keys = ["maintenance_mode", "ai_chatbot_enabled", "allow_new_registrations"]
    configs = db.query(SystemConfig).filter(SystemConfig.key.in_(keys)).all()
    return {c.key: c.value for c in configs}

app.include_router(public_router)


# ─── Health Check ──────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "Sports Injury Detection API is running 🏃"}
