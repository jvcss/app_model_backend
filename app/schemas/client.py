"""
Pydantic schemas for Client organizations.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class ClientBase(BaseModel):
    """Base schema for client-specific data"""
    contract_number: Optional[str] = Field(None, max_length=50)
    billing_info: Optional[Dict[str, Any]] = Field(None, description="Billing information")
    payment_terms: Optional[str] = None


class ClientCreate(ClientBase):
    """Schema for creating client-specific data"""
    pass


class ClientUpdate(BaseModel):
    """Schema for updating client-specific data"""
    contract_number: Optional[str] = Field(None, max_length=50)
    billing_info: Optional[Dict[str, Any]] = None
    payment_terms: Optional[str] = None


class ClientOut(ClientBase):
    """Schema for client output"""
    id: int
    organization_id: int
    created_at: datetime

    class Config:
        from_attributes = True
