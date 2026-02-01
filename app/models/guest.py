from datetime import datetime, timezone
from sqlalchemy import Column, Integer, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base


class Guest(Base):
    """
    Guest-specific data for temporary/limited access organizations.

    Attributes:
        access_expires_at: Datetime when guest access expires
        invited_by: User ID who invited this guest organization
        access_scope: JSON field defining limited permissions/scope
    """
    __tablename__ = "guests"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, unique=True)
    access_expires_at = Column(DateTime(timezone=True), nullable=True)
    invited_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    access_scope = Column(JSON, nullable=True)  # e.g., {"allowed_resources": ["projects"], "read_only": true}
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    organization = relationship("Organization", back_populates="guest")
    inviter = relationship("User", foreign_keys=[invited_by])

    def __repr__(self):
        return f"<Guest(id={self.id}, organization_id={self.organization_id}, expires={self.access_expires_at})>"
