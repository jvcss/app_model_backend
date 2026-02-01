"""
Pydantic schemas for Team Members.

Handles both User and Organization members in teams.
"""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


class TeamMemberBase(BaseModel):
    """Base schema for team member"""
    role: str = Field(..., pattern="^(admin|member|viewer)$")


class TeamMemberAddUser(TeamMemberBase):
    """Schema for adding a User to a team"""
    user_id: int = Field(..., gt=0)


class TeamMemberAddOrganization(TeamMemberBase):
    """Schema for adding an Organization to a team"""
    organization_id: int = Field(..., gt=0)


class TeamMemberUpdate(BaseModel):
    """Schema for updating team member"""
    role: Optional[str] = Field(None, pattern="^(admin|member|viewer)$")
    status: Optional[str] = Field(None, pattern="^(active|inactive|pending)$")


class TeamMemberOut(TeamMemberBase):
    """Schema for team member output"""
    id: int
    team_id: int
    member_type: Literal["user", "organization"]
    member_id: int
    status: str
    invited_at: datetime
    joined_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TeamMemberWithDetails(TeamMemberOut):
    """Team member with detailed information"""
    # For user members
    user_name: Optional[str] = None
    user_email: Optional[str] = None

    # For organization members
    organization_name: Optional[str] = None
    organization_type: Optional[str] = None

    class Config:
        from_attributes = True
