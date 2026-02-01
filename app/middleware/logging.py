"""
Access Logging Middleware

Logs all API requests to database for audit trail and analytics.
Tracks performance, errors, and usage patterns.
"""

import time
import uuid
import hashlib
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.db.session import SessionAsync
from app.models.api_access_log import APIAccessLog

logger = logging.getLogger(__name__)


class AccessLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all API access to database.

    Captures:
    - User context (user_id, organization_id, team_id)
    - Request details (endpoint, method, IP, user agent)
    - Performance metrics (duration, response size)
    - Request tracking (request_id, body hash)
    """

    def __init__(self, app: ASGIApp, enabled: bool = True):
        """
        Initialize the middleware.

        Args:
            app: FastAPI application
            enabled: Whether logging is enabled (can be disabled in tests)
        """
        super().__init__(app)
        self.enabled = enabled

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and log to database.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response from the application
        """
        # Skip if disabled or health check endpoint
        if not self.enabled or request.url.path in ["/", "/health", "/docs", "/openapi.json"]:
            return await call_next(request)

        # Generate request ID for correlation
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Start timer
        start_time = time.time()

        # Extract user context (set by auth middleware)
        user = getattr(request.state, "user", None)
        user_id = user.id if user else None

        # Extract team_id and organization_id from path if available
        team_id = request.path_params.get("team_id")
        organization_id = request.path_params.get("organization_id")

        # Extract client info
        ip_address = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")

        # Hash request body for audit (don't store full body for privacy)
        request_body_hash = None
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    request_body_hash = hashlib.sha256(body).hexdigest()
                # Re-attach body for downstream processing
                async def receive():
                    return {"type": "http.request", "body": body}
                request._receive = receive
            except Exception as e:
                logger.warning(f"Failed to read request body: {e}")

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)

        # Get response size
        response_size = int(response.headers.get("content-length", 0))

        # Log to database asynchronously (fire and forget)
        try:
            await self._log_to_database(
                user_id=user_id,
                organization_id=organization_id,
                team_id=team_id,
                endpoint=request.url.path,
                method=request.method,
                status_code=response.status_code,
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
                duration_ms=duration_ms,
                request_body_hash=request_body_hash,
                response_size=response_size
            )
        except Exception as e:
            # Don't fail request if logging fails
            logger.error(f"Failed to log access: {e}", exc_info=True)

        # Add request ID to response headers for debugging
        response.headers["X-Request-ID"] = request_id

        return response

    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP address from request.

        Checks X-Forwarded-For header first (for proxied requests),
        then falls back to direct client IP.

        Args:
            request: Incoming request

        Returns:
            Client IP address
        """
        # Check X-Forwarded-For header (set by proxies/load balancers)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take first IP in the chain
            return forwarded_for.split(",")[0].strip()

        # Fall back to direct client IP
        if request.client:
            return request.client.host

        return "unknown"

    async def _log_to_database(
        self,
        user_id: int = None,
        organization_id: int = None,
        team_id: int = None,
        endpoint: str = "",
        method: str = "",
        status_code: int = 0,
        ip_address: str = "",
        user_agent: str = "",
        request_id: str = "",
        duration_ms: int = 0,
        request_body_hash: str = None,
        response_size: int = 0
    ):
        """
        Log access information to database.

        Creates a new session to avoid interfering with request handling.

        Args:
            user_id: User ID if authenticated
            organization_id: Organization ID if in context
            team_id: Team ID if in context
            endpoint: Request endpoint path
            method: HTTP method
            status_code: Response status code
            ip_address: Client IP address
            user_agent: User agent string
            request_id: UUID for request correlation
            duration_ms: Request duration in milliseconds
            request_body_hash: SHA256 hash of request body
            response_size: Response size in bytes
        """
        try:
            async with SessionAsync() as db:
                log_entry = APIAccessLog(
                    user_id=user_id,
                    organization_id=organization_id,
                    team_id=team_id,
                    endpoint=endpoint,
                    method=method,
                    status_code=status_code,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    request_id=request_id,
                    duration_ms=duration_ms,
                    request_body_hash=request_body_hash,
                    response_size=response_size
                )
                db.add(log_entry)
                await db.commit()
        except Exception as e:
            # Log error but don't raise (fire and forget)
            logger.error(f"Database logging failed: {e}", exc_info=True)
