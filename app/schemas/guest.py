"""
Pydantic schemas for Guest organizations.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class GuestBase(BaseModel):
    """Base schema for guest-specific data"""
    access_expires_at: Optional[datetime] = None
    access_scope: Optional[Dict[str, Any]] = Field(None, description="Limited access scope")


class GuestCreate(GuestBase):
    """Schema for creating guest-specific data"""
    pass


class GuestUpdate(BaseModel):
    """Schema for updating guest-specific data"""
    access_expires_at: Optional[datetime] = None
    access_scope: Optional[Dict[str, Any]] = None


class GuestOut(GuestBase):
    """Schema for guest output"""
    id: int
    organization_id: int
    invited_by: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True
