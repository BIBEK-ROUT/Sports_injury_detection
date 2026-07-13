from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import engine, Base
from app.api.routes import auth

# Import all models so SQLAlchemy can create their tables
from app.models import user, athlete  # noqa: F401

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

# ─── Routers ───────────────────────────────────────────────────
app.include_router(auth.router)


# ─── Health Check ──────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "Sports Injury Detection API is running 🏃"}
