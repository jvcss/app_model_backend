"""
Pydantic schemas for Organization entities.

Handles validation and serialization for organizations and their members.
"""

from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel, EmailStr, Field


class OrganizationBase(BaseModel):
    """Base schema for organization with common fields"""
    name: str = Field(..., min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = None


class OrganizationCreate(OrganizationBase):
    """Schema for creating a new organization"""
    organization_type: str = Field(..., pattern="^(provider|client|guest)$")


class OrganizationUpdate(BaseModel):
    """Schema for updating an organization"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = None


class OrganizationOut(OrganizationBase):
    """Schema for organization output"""
    id: int
    organization_type: str
    archived: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrganizationWithDetails(OrganizationOut):
    """
    Extended organization schema with type-specific details.

    Includes provider/client/guest-specific fields based on organization_type.
    """
    # Type-specific data (will be populated based on organization_type)
    type_details: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
