from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.base import Base


class TeamMember(Base):
    """
    Polymorphic association table linking Teams to Users OR Organizations.

    Attributes:
        member_type: 'user' or 'organization'
        member_id: Polymorphic FK pointing to either User.id or Organization.id
        role: Member's role in the team ('admin', 'member', 'viewer')
        status: Membership status ('pending', 'active', 'inactive')
    """
    __tablename__ = "team_members"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)

    # Polymorphic fields
    member_type = Column(String(20), nullable=False, index=True)  # 'user' or 'organization'
    member_id = Column(Integer, nullable=False, index=True)  # Polymorphic FK

    # Role and status
    role = Column(String(20), nullable=False)  # 'admin', 'member', 'viewer'
    status = Column(String(20), default="active")  # 'pending', 'active', 'inactive'

    # Audit fields
    invited_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    invited_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    joined_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    team = relationship("Team", back_populates="members")
    inviter = relationship("User", foreign_keys=[invited_by])

    # Constraints
    __table_args__ = (
        UniqueConstraint('team_id', 'member_type', 'member_id', name='uq_team_member'),
    )

    def __repr__(self):
        return f"<TeamMember(team_id={self.team_id}, type='{self.member_type}', member_id={self.member_id}, role='{self.role}')>"

    @property
    def is_user(self):
        """Check if this membership is for a User"""
        return self.member_type == "user"

    @property
    def is_organization(self):
        """Check if this membership is for an Organization"""
        return self.member_type == "organization"

    def get_member(self, db_session):
        """
        Resolve the polymorphic member to actual User or Organization object.

        Args:
            db_session: SQLAlchemy session to query with

        Returns:
            User or Organization object depending on member_type
        """
        if self.is_user:
            from app.models.user import User
            return db_session.query(User).filter(User.id == self.member_id).first()
        elif self.is_organization:
            from app.models.organization import Organization
            return db_session.query(Organization).filter(Organization.id == self.member_id).first()
        return None
