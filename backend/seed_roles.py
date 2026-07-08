"""
Seed script to populate the roles table with default roles.
Run this once after starting the database:
    python seed_roles.py
"""
from app.core.database import SessionLocal
from app.models.user import Role


def seed_roles():
    db = SessionLocal()
    roles = [
        {"name": "athlete", "description": "Sports athlete who uploads videos for analysis"},
        {"name": "coach", "description": "Team coach who monitors athlete performance and risks"},
        {"name": "physiotherapist", "description": "Tracks rehabilitation and injury recovery"},
        {"name": "scientist", "description": "Sports scientist for biomechanical research"},
        {"name": "admin", "description": "Platform administrator with full system access"},
    ]

    for role_data in roles:
        existing = db.query(Role).filter(Role.name == role_data["name"]).first()
        if not existing:
            db.add(Role(**role_data))
            print(f"✅ Added role: {role_data['name']}")
        else:
            print(f"⏭️  Role already exists: {role_data['name']}")

    db.commit()
    db.close()
    print("\n✅ Roles seeded successfully!")


if __name__ == "__main__":
    seed_roles()
