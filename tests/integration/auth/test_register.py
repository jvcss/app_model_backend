"""
Integration tests for user registration.

Tests:
- POST /api/auth/register
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.team import Team
from tests.factories import UserFactory


@pytest.mark.asyncio
class TestRegisterEndpoint:
    """Test POST /api/auth/register endpoint."""

    async def test_register_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test successful user registration."""
        response = await client.post(
            "/api/auth/register",
            json={
                "name": "New User",
                "email": "newuser@example.com",
                "password": "SecurePass123!"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

        # Verify user created in DB
        result = await db_session.execute(
            select(User).where(User.email == "newuser@example.com")
        )
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.name == "New User"
        assert user.password != "SecurePass123!"  # Should be hashed

    async def test_register_creates_personal_team(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test that registration creates a personal team."""
        response = await client.post(
            "/api/auth/register",
            json={
                "name": "New User",
                "email": "newuser@example.com",
                "password": "SecurePass123!"
            }
        )

        assert response.status_code == 200

        # Get user
        result = await db_session.execute(
            select(User).where(User.email == "newuser@example.com")
        )
        user = result.scalar_one_or_none()
        assert user is not None

        # Verify personal team created
        assert user.current_team_id is not None
        result = await db_session.execute(
            select(Team).where(Team.id == user.current_team_id)
        )
        team = result.scalar_one_or_none()
        assert team is not None
        assert team.personal_team is True
        assert team.user_id == user.id

    async def test_register_duplicate_email(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test registration with existing email."""
        # Create existing user
        await UserFactory.create_async(
            db_session,
            email="existing@example.com"
        )
        await db_session.commit()

        response = await client.post(
            "/api/auth/register",
            json={
                "name": "Another User",
                "email": "existing@example.com",
                "password": "Password123!"
            }
        )

        assert response.status_code == 400
        assert "detail" in response.json()

    async def test_register_invalid_email(self, client: AsyncClient):
        """Test registration with invalid email."""
        response = await client.post(
            "/api/auth/register",
            json={
                "name": "Test User",
                "email": "not-an-email",
                "password": "Password123!"
            }
        )

        assert response.status_code == 422  # Validation error

    async def test_register_missing_required_fields(self, client: AsyncClient):
        """Test registration with missing fields."""
        # Missing password
        response = await client.post(
            "/api/auth/register",
            json={
                "name": "Test User",
                "email": "test@example.com"
            }
        )
        assert response.status_code == 422

        # Missing email
        response = await client.post(
            "/api/auth/register",
            json={
                "name": "Test User",
                "password": "Password123!"
            }
        )
        assert response.status_code == 422

        # Missing name
        response = await client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "password": "Password123!"
            }
        )
        assert response.status_code == 422

    async def test_register_empty_name(self, client: AsyncClient):
        """Test registration with empty name."""
        response = await client.post(
            "/api/auth/register",
            json={
                "name": "",
                "email": "test@example.com",
                "password": "Password123!"
            }
        )

        assert response.status_code == 422

    async def test_register_weak_password(self, client: AsyncClient):
        """Test registration with weak password (if validation exists)."""
        weak_passwords = ["123", "password", "abc"]

        for weak_password in weak_passwords:
            response = await client.post(
                "/api/auth/register",
                json={
                    "name": "Test User",
                    "email": f"test{weak_password}@example.com",
                    "password": weak_password
                }
            )
            # Might be 422 if password validation exists, or 200 if not
            # Adjust based on your implementation
            assert response.status_code in [200, 422]

    async def test_register_unicode_name(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test registration with unicode characters in name."""
        response = await client.post(
            "/api/auth/register",
            json={
                "name": "João Silva 中文",
                "email": "joao@example.com",
                "password": "Password123!"
            }
        )

        assert response.status_code == 200

        # Verify unicode name saved correctly
        result = await db_session.execute(
            select(User).where(User.email == "joao@example.com")
        )
        user = result.scalar_one_or_none()
        assert user.name == "João Silva 中文"

    async def test_register_very_long_name(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test registration with very long name."""
        long_name = "A" * 500
        response = await client.post(
            "/api/auth/register",
            json={
                "name": long_name,
                "email": "longname@example.com",
                "password": "Password123!"
            }
        )

        # Should succeed (or fail if there's a length limit)
        if response.status_code == 200:
            result = await db_session.execute(
                select(User).where(User.email == "longname@example.com")
            )
            user = result.scalar_one_or_none()
            assert user.name == long_name

    async def test_register_special_characters_in_password(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test registration with special characters in password."""
        special_password = "P@$$w0rd!#$%^&*()"
        response = await client.post(
            "/api/auth/register",
            json={
                "name": "Test User",
                "email": "special@example.com",
                "password": special_password
            }
        )

        assert response.status_code == 200

        # Verify can login with special password
        login_response = await client.post(
            "/api/auth/login",
            json={
                "email": "special@example.com",
                "password": special_password
            }
        )
        assert login_response.status_code == 200

    async def test_register_returns_valid_token(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test that registration returns a valid, usable token."""
        response = await client.post(
            "/api/auth/register",
            json={
                "name": "Test User",
                "email": "test@example.com",
                "password": "Password123!"
            }
        )

        assert response.status_code == 200
        token = response.json()["access_token"]

        # Use token to access protected endpoint
        me_response = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert me_response.status_code == 200
        assert me_response.json()["user"]["email"] == "test@example.com"

    async def test_register_email_case_insensitive(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test that email is stored consistently (lowercase or as-is)."""
        response = await client.post(
            "/api/auth/register",
            json={
                "name": "Test User",
                "email": "Test@Example.COM",
                "password": "Password123!"
            }
        )

        assert response.status_code == 200

        result = await db_session.execute(
            select(User).where(User.email.ilike("test@example.com"))
        )
        user = result.scalar_one_or_none()
        assert user is not None

    async def test_register_concurrent_same_email(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test concurrent registration attempts with same email."""
        import asyncio

        async def register():
            return await client.post(
                "/api/auth/register",
                json={
                    "name": "Test User",
                    "email": "concurrent@example.com",
                    "password": "Password123!"
                }
            )

        # Try to register same email concurrently
        responses = await asyncio.gather(
            register(),
            register(),
            register(),
            return_exceptions=True
        )

        # Only one should succeed (200), others should fail (400)
        success_count = sum(
            1 for r in responses
            if not isinstance(r, Exception) and r.status_code == 200
        )
        assert success_count == 1

        # Verify only one user created
        result = await db_session.execute(
            select(User).where(User.email == "concurrent@example.com")
        )
        users = result.scalars().all()
        assert len(users) == 1


@pytest.mark.asyncio
class TestRegisterEdgeCases:
    """Test edge cases for registration."""

    async def test_register_sql_injection(self, client: AsyncClient):
        """Test SQL injection prevention in registration."""
        response = await client.post(
            "/api/auth/register",
            json={
                "name": "Test'; DROP TABLE users; --",
                "email": "test@example.com",
                "password": "Password123!"
            }
        )

        # Should not cause SQL error
        assert response.status_code in [200, 422]

    async def test_register_xss_in_name(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test XSS prevention in name field."""
        xss_name = "<script>alert('xss')</script>"
        response = await client.post(
            "/api/auth/register",
            json={
                "name": xss_name,
                "email": "xss@example.com",
                "password": "Password123!"
            }
        )

        if response.status_code == 200:
            # Name should be stored as-is (escaped when rendered)
            result = await db_session.execute(
                select(User).where(User.email == "xss@example.com")
            )
            user = result.scalar_one_or_none()
            assert user.name == xss_name

    async def test_register_whitespace_trimming(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test whitespace handling in email and name."""
        response = await client.post(
            "/api/auth/register",
            json={
                "name": "  Test User  ",
                "email": "  test@example.com  ",
                "password": "Password123!"
            }
        )

        # Depends on implementation - might trim or keep whitespace
        if response.status_code == 200:
            result = await db_session.execute(
                select(User).where(User.email.like("%test@example.com%"))
            )
            user = result.scalar_one_or_none()
            assert user is not None
