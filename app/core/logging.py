"""
Centralized logging configuration with Sentry integration.

Provides structured logging, error tracking, and monitoring capabilities.
"""

import logging
import sys
from typing import Dict, Any, Optional

try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    from sentry_sdk.integrations.redis import RedisIntegration
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False

from app.core.config import settings


def init_sentry():
    """
    Initialize Sentry for error tracking and performance monitoring.

    Only initializes if SENTRY_DSN is configured and sentry-sdk is installed.
    """
    if not SENTRY_AVAILABLE:
        logging.warning("Sentry SDK not installed. Error tracking disabled.")
        return

    sentry_dsn = getattr(settings, 'SENTRY_DSN', None)

    if not sentry_dsn:
        logging.info("SENTRY_DSN not configured. Sentry disabled.")
        return

    try:
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=getattr(settings, 'SENTRY_ENVIRONMENT', settings.MODE),
            traces_sample_rate=float(getattr(settings, 'SENTRY_TRACES_SAMPLE_RATE', 0.1)),
            profiles_sample_rate=0.1,  # Profile 10% of transactions
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
                RedisIntegration(),
            ],
            before_send=filter_sensitive_data,
            # Additional options
            send_default_pii=False,  # Don't send personally identifiable information
            attach_stacktrace=True,
            max_breadcrumbs=50,
        )
        logging.info(f"Sentry initialized successfully for environment: {settings.MODE}")
    except Exception as e:
        logging.error(f"Failed to initialize Sentry: {e}")


def filter_sensitive_data(event: Dict[str, Any], hint: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
    """
    Filter sensitive data before sending to Sentry.

    Removes passwords, tokens, secrets, and other sensitive information
    from request data and headers.

    Args:
        event: Sentry event dictionary
        hint: Sentry hint dictionary

    Returns:
        Modified event with sensitive data removed, or None to drop the event
    """
    # Filter request data
    if 'request' in event and 'data' in event['request']:
        data = event['request']['data']
        if isinstance(data, dict):
            # Remove sensitive fields
            sensitive_fields = [
                'password', 'token', 'secret', 'authorization',
                'api_key', 'access_token', 'refresh_token', 'private_key',
                'credit_card', 'cvv', 'ssn', 'two_factor_secret'
            ]
            for field in sensitive_fields:
                if field in data:
                    data[field] = '[FILTERED]'

    # Filter headers
    if 'request' in event and 'headers' in event['request']:
        headers = event['request']['headers']
        if isinstance(headers, dict):
            sensitive_headers = [
                'Authorization', 'Cookie', 'X-API-Key', 'X-Auth-Token'
            ]
            for header in sensitive_headers:
                if header in headers:
                    headers[header] = '[FILTERED]'

    return event


def capture_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    user: Optional[Dict[str, Any]] = None,
    tags: Optional[Dict[str, str]] = None
) -> Optional[str]:
    """
    Capture an error and send to Sentry with context.

    Args:
        error: Exception to capture
        context: Additional context dict to attach
        user: User information dict (id, email, etc.)
        tags: Tags to attach to the event

    Returns:
        Sentry event ID if sent, None otherwise
    """
    if not SENTRY_AVAILABLE:
        logging.error(f"Error occurred: {error}", exc_info=True)
        return None

    try:
        with sentry_sdk.push_scope() as scope:
            # Add user context
            if user:
                scope.set_user({
                    "id": user.get("id"),
                    "email": user.get("email"),
                    "username": user.get("name")
                })

            # Add custom context
            if context:
                for key, value in context.items():
                    scope.set_context(key, value)

            # Add tags
            if tags:
                for key, value in tags.items():
                    scope.set_tag(key, value)

            # Capture exception
            event_id = sentry_sdk.capture_exception(error)
            logging.info(f"Error captured in Sentry with event ID: {event_id}")
            return event_id
    except Exception as e:
        logging.error(f"Failed to capture error in Sentry: {e}")
        logging.error(f"Original error: {error}", exc_info=True)
        return None


def setup_logging():
    """
    Configure structured logging for the application.

    Sets up log formatters, handlers, and log levels.
    """
    log_level = getattr(settings, 'LOG_LEVEL', 'INFO')

    # Create logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    logger.handlers = []

    # Console handler with formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))

    # Format
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    logging.info(f"Logging configured with level: {log_level}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
