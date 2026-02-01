from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, BigInteger, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from app.db.base import Base


class ErrorLog(Base):
    """
    Application error logging for tracking and resolution.

    Captures exceptions, errors, and warnings with full context
    for debugging and monitoring. Integrates with Sentry via event_id.
    """
    __tablename__ = "error_logs"

    id = Column(BigInteger, primary_key=True, index=True)

    # User context (if error occurred during authenticated request)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Error details
    error_type = Column(String(100), nullable=False)  # Exception class name
    error_message = Column(Text, nullable=False)
    stack_trace = Column(Text, nullable=True)

    # Request context
    endpoint = Column(String(255), nullable=True)
    method = Column(String(10), nullable=True)
    request_id = Column(String(36), nullable=True, index=True)  # UUID for correlation with APIAccessLog

    # Sentry integration
    sentry_event_id = Column(String(36), nullable=True, index=True)  # Link to Sentry event

    # Client information
    ip_address = Column(String(45), nullable=True)

    # Severity and resolution
    severity = Column(String(20), nullable=True)  # 'debug', 'info', 'warning', 'error', 'critical'
    resolved = Column(Boolean, default=False, index=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Timestamp
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    resolver = relationship("User", foreign_keys=[resolved_by])

    def __repr__(self):
        return f"<ErrorLog(id={self.id}, type='{self.error_type}', severity='{self.severity}', resolved={self.resolved})>"
