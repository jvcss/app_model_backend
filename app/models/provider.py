from datetime import datetime, timezone
from sqlalchemy import Column, Integer, ForeignKey, Boolean, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base


class Provider(Base):
    """
    Provider-specific data for organizations that provide services.

    Attributes:
        services_offered: JSON field with list of services
        capabilities: JSON field with provider capabilities
        certification_info: Text field for certifications/credentials
        verified: Boolean indicating if provider is verified/approved
    """
    __tablename__ = "providers"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, unique=True)
    services_offered = Column(JSON, nullable=True)  # e.g., ["consulting", "development", "support"]
    capabilities = Column(JSON, nullable=True)  # e.g., {"languages": ["Python", "JavaScript"], "frameworks": ["FastAPI", "React"]}
    certification_info = Column(Text, nullable=True)
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    organization = relationship("Organization", back_populates="provider")

    def __repr__(self):
        return f"<Provider(id={self.id}, organization_id={self.organization_id}, verified={self.verified})>"
