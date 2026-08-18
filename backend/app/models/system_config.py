"""
SystemConfig — Global platform settings controlled by the Admin.

Each setting is stored as a key-value pair. This allows the Admin Dashboard
to toggle features on/off (e.g., maintenance mode, AI chatbot) without
requiring a server restart or code change.
"""

from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text
from app.core.database import Base


class SystemConfig(Base):
    """Key-value store for global platform settings."""
    __tablename__ = "system_config"

    key         = Column(String(100), primary_key=True, index=True)
    value       = Column(Text, nullable=False)             # stored as string ("true"/"false" or JSON)
    description = Column(String(255), nullable=True)       # human-readable label for the Admin UI
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# ─── Default settings seeded on first boot ─────────────────────────────────
DEFAULT_CONFIGS = [
    {
        "key": "maintenance_mode",
        "value": "false",
        "description": "When enabled, all users see a maintenance screen and cannot use the platform.",
    },
    {
        "key": "ai_chatbot_enabled",
        "value": "true",
        "description": "When disabled, the Sporty AI chatbot is hidden from all users.",
    },
    {
        "key": "allow_new_registrations",
        "value": "true",
        "description": "When disabled, new users cannot register an account.",
    },
]
