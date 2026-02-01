"""
Pydantic schemas for Provider organizations.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ProviderBase(BaseModel):
    """Base schema for provider-specific data"""
    services_offered: Optional[List[str]] = Field(None, description="List of services offered")
    capabilities: Optional[Dict[str, Any]] = Field(None, description="Provider capabilities")
    certification_info: Optional[str] = None


class ProviderCreate(ProviderBase):
    """Schema for creating provider-specific data"""
    pass


class ProviderUpdate(BaseModel):
    """Schema for updating provider-specific data"""
    services_offered: Optional[List[str]] = None
    capabilities: Optional[Dict[str, Any]] = None
    certification_info: Optional[str] = None


class ProviderOut(ProviderBase):
    """Schema for provider output"""
    id: int
    organization_id: int
    verified: bool
    created_at: datetime

    class Config:
        from_attributes = True
