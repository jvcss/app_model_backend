"""
Global test fixtures and configuration.

This module provides base fixtures for all tests:
- Event loop configuration
- Database session with automatic rollback
- Redis client (in-memory fake)
- HTTP client with dependency overrides
- Base data fixtures (user, team, auth_headers)
"""

import os
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from fakeredis import FakeAsyncRedis

# Set test environment variables BEFORE importing app
os.environ["MODE"] = "test"
os.environ["POSTGRES_INTERNAL_URL"] = "postgresql+asyncpg://test_user:test_pass@localhost:5432/test_app_db"
os.environ["POSTGRES_INTERNAL_URL_SYNC"] = "postgresql+psycopg2://test_user:test_pass@localhost:5432/test_app_db"
os.environ["CELERY_BROKER_URL"] = "redis://localhost:6379/1"
os.environ["CELERY_RESULT_BACKEND"] = "redis://localhost:6379/1"

from app.main import app
from app.api.dependencies import get_db, get_redis
from app.db.base import Base

# Test database URL
TEST_DATABASE_URL = os.environ["POSTGRES_INTERNAL_URL"]

# ==================== Event Loop ====================

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """
    Create event loop for entire test session.

    Session-scoped to avoid creating/closing loop per test.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ==================== Database ====================

@pytest.fixture(scope="session")
async def test_engine():
    """
    Create test database engine (session-scoped).

    Creates all tables before tests and drops them after.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,  # No connection pooling in tests
        echo=False  # Set to True for SQL debugging
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables after all tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create isolated DB session for each test with automatic rollback.

    Each test runs in a transaction that's rolled back after completion.
    This ensures test isolation without needing to manually clean up data.
    """
    connection = await test_engine.connect()
    transaction = await connection.begin()

    session_factory = sessionmaker(
        bind=connection,
        class_=AsyncSession,
        expire_on_commit=False
    )
    session = session_factory()

    yield session

    # Cleanup
    await session.close()
    await transaction.rollback()
    await connection.close()


# ==================== Redis ====================

@pytest.fixture(scope="function")
async def redis_client() -> AsyncGenerator[FakeAsyncRedis, None]:
    """
    Create fake Redis client (in-memory) for each test.

    FakeRedis is much faster than real Redis for unit tests.
    Use real Redis for integration tests if needed.
    """
    redis = FakeAsyncRedis()
    yield redis
    await redis.flushall()
    await redis.close()


# ==================== FastAPI Client ====================

@pytest.fixture(scope="function")
async def client(
    db_session: AsyncSession,
    redis_client: FakeAsyncRedis
) -> AsyncGenerator[AsyncClient, None]:
    """
    Create HTTP client for testing FastAPI endpoints.

    Overrides get_db and get_redis dependencies to use test fixtures.
    """

    async def override_get_db():
        yield db_session

    async def override_get_redis():
        yield redis_client

    # Override dependencies
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    # Clear overrides after test
    app.dependency_overrides.clear()


# ==================== Base Data Fixtures ====================

@pytest.fixture
async def user(db_session: AsyncSession):
    """
    Create a test user with personal team.

    This fixture will be implemented after factories are created.
    For now, it's a placeholder.
    """
    # Will be implemented in Phase 2 with UserFactory
    from tests.factories.user import UserFactory
    user = await UserFactory.create_async(db_session)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def admin_user(db_session: AsyncSession):
    """
    Create admin user for testing admin-only endpoints.
    """
    from tests.factories.user import UserFactory
    user = await UserFactory.create_async(
        db_session,
        email="admin@test.com",
        name="Admin User"
    )
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def auth_headers(user):
    """
    Generate authentication headers for authenticated requests.

    Creates a valid JWT token for the user.
    """
    from app.core.security import create_access_token

    token = create_access_token(
        data={"sub": str(user.id)},
        token_version=user.token_version
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def admin_auth_headers(admin_user):
    """
    Generate authentication headers for admin user.
    """
    from app.core.security import create_access_token

    token = create_access_token(
        data={"sub": str(admin_user.id)},
        token_version=admin_user.token_version
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def team(db_session: AsyncSession, user):
    """
    Create a team owned by user.
    """
    from tests.factories.team import TeamFactory
    team = await TeamFactory.create_async(db_session, user_id=user.id)
    await db_session.commit()
    await db_session.refresh(team)
    return team


@pytest.fixture
async def organization(db_session: AsyncSession):
    """
    Create a test organization (provider type).
    """
    from tests.factories.organization import OrganizationFactory
    org = await OrganizationFactory.create_async(
        db_session,
        organization_type="provider"
    )
    await db_session.commit()
    await db_session.refresh(org)
    return org


# ==================== Helper Fixtures ====================

@pytest.fixture
def anyio_backend():
    """
    Configure anyio backend for httpx AsyncClient.
    """
    return "asyncio"
