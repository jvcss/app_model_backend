from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.base import Base

class Team(Base):
    __tablename__ = "teams"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String(50), index=True)
    description = Column(Text, nullable=True)  # New: Team description
    personal_team = Column(Boolean, default=False)
    archived = Column(Boolean, default=False)  # New: Soft delete
    archived_at = Column(DateTime(timezone=True), nullable=True)  # New: When archived
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    owner = relationship("User", foreign_keys=[user_id], back_populates="teams")
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")  # New: Multi-user support
