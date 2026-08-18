"""
create_admin.py — One-time script to create the platform Super Admin account.

Run this script exactly ONCE to inject an Administrator account into the database.
This works for both:
  - Local development (SQLite)
  - Production (Supabase / PostgreSQL) — just make sure your .env points to the cloud DB

Usage:
    cd backend
    python scripts/create_admin.py
"""

import sys
import os

# Add the backend root to the Python path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from app.core.database import SessionLocal, engine, Base
from app.core.security import hash_password
from app.models.user import User, Role
from app.models import user, athlete, video_analysis  # noqa - ensures tables are created
from app.models.system_config import SystemConfig  # noqa

# Create all tables including system_config
Base.metadata.create_all(bind=engine)


def create_admin():
    db = SessionLocal()
    try:
        # -- Make sure the admin role exists ------------------------------
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if not admin_role:
            print("[ERROR] 'admin' role not found in the database.")
            print("   Please run: python seed_roles.py first.")
            return

        print("\n======================================")
        print("  Sports Injury Platform Admin Setup  ")
        print("======================================\n")

        email = input("Enter admin email address: ").strip().lower()
        if not email:
            print("[ERROR] Email cannot be empty.")
            return

        # Check if email is already taken
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f"[ERROR] An account with email '{email}' already exists.")
            return

        password = input("Enter admin password (min 8 characters): ").strip()
        if len(password) < 8:
            print("[ERROR] Password must be at least 8 characters.")
            return

        first_name = input("Enter first name: ").strip()
        last_name  = input("Enter last name: ").strip()

        # -- Create the admin user -----------------------------------------
        admin_user = User(
            email=email,
            hashed_password=hash_password(password),
            first_name=first_name,
            last_name=last_name,
            role_id=admin_role.id,
            is_active=True,
            invite_code=None,
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        print(f"\n[OK] Admin account created successfully!")
        print(f"   Email:    {email}")
        print(f"   Name:     {first_name} {last_name}")
        print(f"   Role:     Administrator")
        print(f"\n   You can now log in at the frontend with these credentials.\n")

    except Exception as e:
        print(f"\n[ERROR] An error occurred: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    create_admin()
