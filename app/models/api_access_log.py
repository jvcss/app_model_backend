from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, BigInteger, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from app.db.base import Base


class APIAccessLog(Base):
    """
    Comprehensive API access logging for audit and analytics.

    Tracks all API requests with user context, performance metrics,
    and request/response metadata.
    """
    __tablename__ = "api_access_logs"

    id = Column(BigInteger, primary_key=True, index=True)

    # User/Organization context
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True)

    # Request information
    endpoint = Column(String(255), nullable=False, index=True)
    method = Column(String(10), nullable=False)  # GET, POST, PUT, DELETE, etc.
    status_code = Column(Integer, nullable=False)

    # Client information
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)

    # Correlation and tracking
    request_id = Column(String(36), nullable=True, unique=True, index=True)  # UUID for request correlation

    # Performance metrics
    duration_ms = Column(Integer, nullable=True)  # Request duration in milliseconds

    # Security and audit
    request_body_hash = Column(String(64), nullable=True)  # SHA256 hash of request body
    response_size = Column(Integer, nullable=True)  # Response size in bytes

    # Timestamp
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    organization = relationship("Organization", foreign_keys=[organization_id])
    team = relationship("Team", foreign_keys=[team_id])

    def __repr__(self):
        return f"<APIAccessLog(id={self.id}, endpoint='{self.endpoint}', method='{self.method}', status={self.status_code})>"
