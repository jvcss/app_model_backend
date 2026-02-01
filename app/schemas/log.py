"""
Pydantic schemas for Logs.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class APIAccessLogOut(BaseModel):
    """Schema for API access log output"""
    id: int
    user_id: Optional[int] = None
    organization_id: Optional[int] = None
    team_id: Optional[int] = None
    endpoint: str
    method: str
    status_code: int
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    duration_ms: Optional[int] = None
    response_size: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ErrorLogOut(BaseModel):
    """Schema for error log output"""
    id: int
    user_id: Optional[int] = None
    error_type: str
    error_message: str
    endpoint: Optional[str] = None
    method: Optional[str] = None
    request_id: Optional[str] = None
    sentry_event_id: Optional[str] = None
    ip_address: Optional[str] = None
    severity: Optional[str] = None
    resolved: bool
    resolved_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ErrorLogResolve(BaseModel):
    """Schema for resolving an error log"""
    resolved: bool = True


class LogAnalytics(BaseModel):
    """Schema for log analytics summary"""
    total_requests: int
    unique_users: int
    avg_response_time_ms: float
    error_rate: float
    top_endpoints: list[dict]
    requests_by_status: dict[int, int]
