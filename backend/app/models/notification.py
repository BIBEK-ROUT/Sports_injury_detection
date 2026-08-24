import uuid
from datetime import datetime
from sqlalchemy import Column, String, ForeignKey, DateTime, Text, Boolean
from app.core.database import Base
from app.models.user import UUID


class Notification(Base):
    """In-app alert for Coach / Physiotherapist when an athlete is flagged with high or critical risk."""
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    recipient_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    athlete_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    athlete_name = Column(String(255), nullable=False)
    session_id = Column(String(100), nullable=True)
    risk_level = Column(String(50), nullable=False)  # "high", "critical", "unlinked"
    sport_type = Column(String(100), nullable=True)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
