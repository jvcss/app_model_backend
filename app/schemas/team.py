"""
Pydantic schemas for Team entities.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TeamBase(BaseModel):
    """Base schema for team with common fields"""
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None


class TeamCreate(TeamBase):
    """Schema for creating a new team"""
    personal_team: bool = False


class TeamUpdate(BaseModel):
    """Schema for updating a team"""
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = None


class TeamOut(TeamBase):
    """Schema for team output"""
    id: int
    user_id: int  # Owner ID
    personal_team: bool
    archived: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TeamWithMembers(TeamOut):
    """Team schema with member count"""
    member_count: Optional[int] = None

    class Config:
        from_attributes = True
