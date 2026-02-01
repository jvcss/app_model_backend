"""
Logs API Endpoints

Provides read-only access to API access logs and error logs.
Admin-only endpoints for monitoring and troubleshooting.
"""

from typing import List, Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.models.api_access_log import APIAccessLog
from app.models.error_log import ErrorLog
from app.schemas.log import (
    APIAccessLogOut,
    ErrorLogOut,
    ErrorLogResolve,
    LogAnalytics
)

router = APIRouter()


# TODO: Add proper admin check - for now, all authenticated users can access
# In production, add: current_user: User = Depends(require_admin)


@router.get("/access", response_model=List[APIAccessLogOut])
async def list_access_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    user_id: Optional[int] = None,
    endpoint: Optional[str] = None,
    method: Optional[str] = None,
    status_code: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List API access logs.

    Query parameters:
    - skip: Number of records to skip
    - limit: Maximum number of records to return
    - user_id: Filter by user ID
    - endpoint: Filter by endpoint path
    - method: Filter by HTTP method
    - status_code: Filter by status code
    - start_date: Filter logs after this date
    - end_date: Filter logs before this date
    """
    query = select(APIAccessLog)

    # Apply filters
    filters = []
    if user_id:
        filters.append(APIAccessLog.user_id == user_id)
    if endpoint:
        filters.append(APIAccessLog.endpoint.contains(endpoint))
    if method:
        filters.append(APIAccessLog.method == method.upper())
    if status_code:
        filters.append(APIAccessLog.status_code == status_code)
    if start_date:
        filters.append(APIAccessLog.created_at >= start_date)
    if end_date:
        filters.append(APIAccessLog.created_at <= end_date)

    if filters:
        query = query.filter(and_(*filters))

    # Order by most recent first
    query = query.order_by(desc(APIAccessLog.created_at))

    # Apply pagination
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    logs = result.scalars().all()

    return logs


@router.get("/errors", response_model=List[ErrorLogOut])
async def list_error_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    user_id: Optional[int] = None,
    error_type: Optional[str] = None,
    severity: Optional[str] = None,
    resolved: Optional[bool] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List error logs.

    Query parameters:
    - skip: Number of records to skip
    - limit: Maximum number of records to return
    - user_id: Filter by user ID
    - error_type: Filter by error type
    - severity: Filter by severity level
    - resolved: Filter by resolution status
    - start_date: Filter errors after this date
    - end_date: Filter errors before this date
    """
    query = select(ErrorLog)

    # Apply filters
    filters = []
    if user_id:
        filters.append(ErrorLog.user_id == user_id)
    if error_type:
        filters.append(ErrorLog.error_type.contains(error_type))
    if severity:
        filters.append(ErrorLog.severity == severity)
    if resolved is not None:
        filters.append(ErrorLog.resolved == resolved)
    if start_date:
        filters.append(ErrorLog.created_at >= start_date)
    if end_date:
        filters.append(ErrorLog.created_at <= end_date)

    if filters:
        query = query.filter(and_(*filters))

    # Order by most recent first
    query = query.order_by(desc(ErrorLog.created_at))

    # Apply pagination
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    logs = result.scalars().all()

    return logs


@router.patch("/errors/{error_id}", response_model=ErrorLogOut)
async def resolve_error(
    error_id: int,
    resolve_data: ErrorLogResolve,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark an error as resolved.

    Only admins can resolve errors.
    """
    result = await db.execute(
        select(ErrorLog).filter(ErrorLog.id == error_id)
    )
    error_log = result.scalar_one_or_none()

    if not error_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Error log not found"
        )

    error_log.resolved = resolve_data.resolved
    if resolve_data.resolved:
        error_log.resolved_at = datetime.now(timezone.utc)
        error_log.resolved_by = current_user.id

    await db.commit()
    await db.refresh(error_log)

    return error_log


@router.get("/analytics", response_model=LogAnalytics)
async def get_log_analytics(
    hours: int = Query(24, ge=1, le=720),  # Last 24 hours by default, max 30 days
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get analytics summary for API access logs.

    Query parameters:
    - hours: Number of hours to analyze (default: 24, max: 720)
    """
    # Calculate time range
    start_time = datetime.now(timezone.utc) - timedelta(hours=hours)

    # Total requests
    total_requests_query = select(func.count(APIAccessLog.id)).filter(
        APIAccessLog.created_at >= start_time
    )
    total_requests_result = await db.execute(total_requests_query)
    total_requests = total_requests_result.scalar() or 0

    # Unique users
    unique_users_query = select(func.count(func.distinct(APIAccessLog.user_id))).filter(
        APIAccessLog.created_at >= start_time,
        APIAccessLog.user_id.isnot(None)
    )
    unique_users_result = await db.execute(unique_users_query)
    unique_users = unique_users_result.scalar() or 0

    # Average response time
    avg_response_time_query = select(func.avg(APIAccessLog.duration_ms)).filter(
        APIAccessLog.created_at >= start_time,
        APIAccessLog.duration_ms.isnot(None)
    )
    avg_response_time_result = await db.execute(avg_response_time_query)
    avg_response_time_ms = float(avg_response_time_result.scalar() or 0)

    # Error rate (4xx and 5xx status codes)
    error_count_query = select(func.count(APIAccessLog.id)).filter(
        APIAccessLog.created_at >= start_time,
        APIAccessLog.status_code >= 400
    )
    error_count_result = await db.execute(error_count_query)
    error_count = error_count_result.scalar() or 0
    error_rate = (error_count / total_requests * 100) if total_requests > 0 else 0

    # Top endpoints
    top_endpoints_query = (
        select(
            APIAccessLog.endpoint,
            func.count(APIAccessLog.id).label('count')
        )
        .filter(APIAccessLog.created_at >= start_time)
        .group_by(APIAccessLog.endpoint)
        .order_by(desc('count'))
        .limit(10)
    )
    top_endpoints_result = await db.execute(top_endpoints_query)
    top_endpoints = [
        {"endpoint": row[0], "count": row[1]}
        for row in top_endpoints_result.all()
    ]

    # Requests by status code
    status_query = (
        select(
            APIAccessLog.status_code,
            func.count(APIAccessLog.id).label('count')
        )
        .filter(APIAccessLog.created_at >= start_time)
        .group_by(APIAccessLog.status_code)
    )
    status_result = await db.execute(status_query)
    requests_by_status = {
        row[0]: row[1]
        for row in status_result.all()
    }

    return LogAnalytics(
        total_requests=total_requests,
        unique_users=unique_users,
        avg_response_time_ms=round(avg_response_time_ms, 2),
        error_rate=round(error_rate, 2),
        top_endpoints=top_endpoints,
        requests_by_status=requests_by_status
    )
