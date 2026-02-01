"""
Pydantic schemas for Organization Members.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class OrganizationMemberBase(BaseModel):
    """Base schema for organization member"""
    role: str = Field(..., pattern="^(admin|member)$")


class OrganizationMemberCreate(OrganizationMemberBase):
    """Schema for adding a member to an organization"""
    user_id: int = Field(..., gt=0)


class OrganizationMemberUpdate(BaseModel):
    """Schema for updating organization member"""
    role: Optional[str] = Field(None, pattern="^(admin|member)$")
    status: Optional[str] = Field(None, pattern="^(active|inactive|pending)$")


class OrganizationMemberOut(OrganizationMemberBase):
    """Schema for organization member output"""
    id: int
    organization_id: int
    user_id: int
    status: str
    joined_at: datetime

    class Config:
        from_attributes = True


class OrganizationMemberWithUser(OrganizationMemberOut):
    """Organization member with user details"""
    user_name: Optional[str] = None
    user_email: Optional[str] = None

    class Config:
        from_attributes = True
