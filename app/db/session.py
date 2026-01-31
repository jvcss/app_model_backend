from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.helpers.getters import isDebugMode
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

POSTGRES_INTERNAL_URL = settings.POSTGRES_INTERNAL_URL
POSTGRES_INTERNAL_URL_SYNC = settings.POSTGRES_INTERNAL_URL_SYNC

POSTGRES_EXTERNAL_URL = settings.POSTGRES_EXTERNAL_URL
POSTGRES_EXTERNAL_URL_SYNC = settings.POSTGRES_EXTERNAL_URL_SYNC

if isDebugMode():
    logger.info("Using EXTERNAL database URL for debug mode")
    # PostgreSQL EXTERNAL URL LOCALHOST
    engine_internal = create_async_engine(POSTGRES_EXTERNAL_URL, future=True, echo=False)
    SessionAsync = sessionmaker(engine_internal, class_=AsyncSession, expire_on_commit=False)
    # PostgreSQL EXTERNAL URL LOCALHOST sync
    engine_internal_sync = create_engine(POSTGRES_EXTERNAL_URL_SYNC, pool_pre_ping=True)
    SessionSync = sessionmaker(bind=engine_internal_sync, expire_on_commit=False)
else:
    logger.info("Using INTERNAL database URL for production mode")
    # PostgreSQL internal
    engine_internal = create_async_engine(POSTGRES_INTERNAL_URL, future=True, echo=False)
    SessionAsync = sessionmaker(engine_internal, class_=AsyncSession, expire_on_commit=False)

    # PostgreSQL internal sync
    engine_internal_sync = create_engine(POSTGRES_INTERNAL_URL_SYNC, pool_pre_ping=True)
    SessionSync = sessionmaker(bind=engine_internal_sync, expire_on_commit=False)