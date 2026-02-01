from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from app.db.base import Base


class Organization(Base):
    """
    Base organization model for Provider, Client, and Guest entities.

    Organizations represent companies/entities that can:
    - Have multiple users as members
    - Participate in teams
    - Have type-specific attributes (provider/client/guest)
    """
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    organization_type = Column(String(20), nullable=False, index=True)  # 'provider', 'client', 'guest'
    email = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    archived = Column(Boolean, default=False)

    # Relationships
    members = relationship("OrganizationMember", back_populates="organization", cascade="all, delete-orphan")
    team_memberships = relationship("TeamMember", foreign_keys="[TeamMember.member_id]", primaryjoin="and_(TeamMember.member_id==Organization.id, TeamMember.member_type=='organization')", viewonly=True)

    # Type-specific relationships (1:1)
    provider = relationship("Provider", back_populates="organization", uselist=False, cascade="all, delete-orphan")
    client = relationship("Client", back_populates="organization", uselist=False, cascade="all, delete-orphan")
    guest = relationship("Guest", back_populates="organization", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Organization(id={self.id}, name='{self.name}', type='{self.organization_type}')>"
