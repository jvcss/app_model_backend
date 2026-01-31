# app/models/password_reset.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone, timedelta
from app.db.base import Base

class PasswordReset(Base):
    __tablename__ = "password_resets"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    email = Column(String(100), index=True, nullable=False)
    otp_hash = Column(String(255), nullable=True)  # bcrypt of 6-digit OTP
    otp_expires_at = Column(DateTime(timezone=True), nullable=True)
    otp_verified = Column(Boolean, default=False, nullable=False)

    require_totp = Column(Boolean, default=False, nullable=False)
    totp_verified = Column(Boolean, default=False, nullable=False)

    reset_session_issued_at = Column(DateTime(timezone=True), nullable=True)
    consumed_at = Column(DateTime(timezone=True), nullable=True)

    attempts = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User")
