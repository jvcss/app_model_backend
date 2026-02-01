from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.base import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), index=True)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password = Column(String(150), nullable=False)
    # Usa use_alter=True para quebrar o ciclo
    current_team_id = Column(Integer, ForeignKey("teams.id", use_alter=True, name="fk_users_current_team_id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    # New fields for tracking and localization
    last_active_at = Column(DateTime(timezone=True), nullable=True)
    timezone = Column(String(50), default="UTC")

    # Relacionamento com os times onde o usuário é o dono (usando a coluna Team.user_id)
    teams = relationship("Team", foreign_keys="[Team.user_id]", back_populates="owner")
    # Relacionamento opcional para acessar o time atual do usuário
    current_team = relationship("Team", foreign_keys=[current_team_id], post_update=True)
    # New: Team memberships (as member, not owner)
    team_memberships = relationship("TeamMember", foreign_keys="[TeamMember.member_id]", primaryjoin="and_(TeamMember.member_id==User.id, TeamMember.member_type=='user')", viewonly=True)
    # New: Organization memberships
    organization_memberships = relationship("OrganizationMember", back_populates="user")

    # Campos para autenticação de dois fatores
    two_factor_enabled = Column(Boolean, default=False, nullable=False)
    two_factor_secret = Column(String(64), nullable=True)      # base32 TOTP secret
    token_version = Column(Integer, default=1, nullable=False) # invalidate old JWTs

