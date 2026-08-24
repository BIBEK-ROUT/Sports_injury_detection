"""
Pytest configuration & fixtures for SportGuard test suite.
Uses an isolated in-memory SQLite database (sqlite:///:memory:) so no actual
production or local development database records are touched during testing.
"""

import os
import uuid
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure test environment variables are set before imports
os.environ["SECRET_KEY"] = "test_super_secret_jwt_key_1234567890_sportguard"
os.environ["ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"

# Import all SQLAlchemy models so relationships resolve
from app.core.database import Base, get_db
from app.models.user import Role, User
from app.models.athlete import AthleteProfile, InjuryHistory
from app.models.video_analysis import VideoAnalysis
from app.models.notification import Notification
from app.models.system_config import SystemConfig, DEFAULT_CONFIGS
from app.core.security import hash_password, create_access_token
from main import app

import sqlite3
# Register SQLite UUID adapters so in-memory SQLite handles UUID columns seamlessly
sqlite3.register_adapter(uuid.UUID, lambda u: str(u))

# In-memory SQLite database engine shared across threads for testing
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Creates database schema once for the test session."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    """Provides a transactional database session for each test function."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    # Seed default roles (Role.id is Integer auto-increment)
    roles = ["athlete", "coach", "physiotherapist", "scientist", "admin"]
    for r_name in roles:
        if not session.query(Role).filter(Role.name == r_name).first():
            session.add(Role(name=r_name, description=f"{r_name.capitalize()} role"))

    # Seed default system configs
    for cfg in DEFAULT_CONFIGS:
        if not session.query(SystemConfig).filter(SystemConfig.key == cfg["key"]).first():
            session.add(SystemConfig(**cfg))

    session.commit()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI TestClient with overridden get_db dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_roles(db_session):
    """Returns mapping of role names to Role instances."""
    return {r.name: r for r in db_session.query(Role).all()}


@pytest.fixture(scope="function")
def athlete_user(db_session, test_roles):
    """Creates a standard test athlete user."""
    user = User(
        id=uuid.uuid4(),
        email="test_athlete@sportguard.com",
        first_name="Alex",
        last_name="Runner",
        hashed_password=hash_password("Password123!"),
        role_id=test_roles["athlete"].id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Create athlete profile
    profile = AthleteProfile(
        id=uuid.uuid4(),
        user_id=user.id,
        sport_type="BASKETBALL",
        position="Point Guard",
        dominant_limb="RIGHT",
        age=22,
        height_cm=185.0,
        weight_kg=78.0,
        weekly_training_hours=12,
    )
    db_session.add(profile)
    db_session.commit()
    return user


@pytest.fixture(scope="function")
def coach_user(db_session, test_roles):
    """Creates a test coach user with an invite code."""
    user = User(
        id=uuid.uuid4(),
        email="test_coach@sportguard.com",
        first_name="Sarah",
        last_name="Coach",
        hashed_password=hash_password("Password123!"),
        role_id=test_roles["coach"].id,
        is_active=True,
        invite_code="COACH999",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def physio_user(db_session, test_roles):
    """Creates a test physiotherapist user with an invite code."""
    user = User(
        id=uuid.uuid4(),
        email="test_physio@sportguard.com",
        first_name="Dr. Mark",
        last_name="Physio",
        hashed_password=hash_password("Password123!"),
        role_id=test_roles["physiotherapist"].id,
        is_active=True,
        invite_code="PHYSIO888",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def admin_user(db_session, test_roles):
    """Creates a test admin user."""
    user = User(
        id=uuid.uuid4(),
        email="test_admin@sportguard.com",
        first_name="Root",
        last_name="Admin",
        hashed_password=hash_password("AdminSecret123!"),
        role_id=test_roles["admin"].id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_headers_athlete(athlete_user):
    token = create_access_token(data={"sub": str(athlete_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def auth_headers_coach(coach_user):
    token = create_access_token(data={"sub": str(coach_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def auth_headers_physio(physio_user):
    token = create_access_token(data={"sub": str(physio_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def auth_headers_admin(admin_user):
    token = create_access_token(data={"sub": str(admin_user.id)})
    return {"Authorization": f"Bearer {token}"}
