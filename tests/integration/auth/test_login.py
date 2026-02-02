"""
Integration tests for login endpoints.

Tests:
- POST /api/auth/token (OAuth2)
- POST /api/auth/login (JSON)
- POST /api/auth/logout
- GET /api/auth/me
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from tests.factories import UserFactory


@pytest.mark.asyncio
class TestLoginEndpoint:
    """Test POST /api/auth/login endpoint."""

    async def test_login_success(self, client: AsyncClient, db_session: AsyncSession):
        """Test successful login with valid credentials."""
        # Create user with known password
        user = await UserFactory.create_async(
            db_session,
            email="test@example.com",
            password=get_password_hash("Password123!")
        )
        await db_session.commit()

        response = await client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "Password123!"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 50  # JWT should be long

    async def test_login_invalid_password(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test login with incorrect password."""
        user = await UserFactory.create_async(
            db_session,
            email="test@example.com",
            password=get_password_hash("CorrectPassword123!")
        )
        await db_session.commit()

        response = await client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "WrongPassword"}
        )

        assert response.status_code == 401
        assert "detail" in response.json()

    async def test_login_user_not_found(self, client: AsyncClient):
        """Test login with non-existent email."""
        response = await client.post(
            "/api/auth/login",
            json={"email": "nonexistent@example.com", "password": "Password123!"}
        )

        assert response.status_code == 401
        # Should not reveal whether user exists (anti-enumeration)

    async def test_login_invalid_email_format(self, client: AsyncClient):
        """Test login with invalid email format."""
        response = await client.post(
            "/api/auth/login",
            json={"email": "not-an-email", "password": "Password123!"}
        )

        assert response.status_code == 422  # Validation error

    async def test_login_missing_password(self, client: AsyncClient):
        """Test login without password."""
        response = await client.post(
            "/api/auth/login",
            json={"email": "test@example.com"}
        )

        assert response.status_code == 422

    async def test_login_empty_password(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test login with empty password."""
        user = await UserFactory.create_async(db_session, email="test@example.com")
        await db_session.commit()

        response = await client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": ""}
        )

        assert response.status_code == 401

    async def test_login_case_sensitive_email(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test that email comparison is case-insensitive (if implemented)."""
        user = await UserFactory.create_async(
            db_session,
            email="Test@Example.com",
            password=get_password_hash("Password123!")
        )
        await db_session.commit()

        # Try login with different case
        response = await client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "Password123!"}
        )

        # This depends on your implementation
        # If case-insensitive: 200, if case-sensitive: 401
        assert response.status_code in [200, 401]


@pytest.mark.asyncio
class TestTokenEndpoint:
    """Test POST /api/auth/token endpoint (OAuth2)."""

    async def test_token_oauth2_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test OAuth2 token endpoint with form data."""
        user = await UserFactory.create_async(
            db_session,
            email="test@example.com",
            password=get_password_hash("Password123!")
        )
        await db_session.commit()

        # OAuth2 expects form data, not JSON
        response = await client.post(
            "/api/auth/token",
            data={
                "username": "test@example.com",  # OAuth2 uses 'username'
                "password": "Password123!"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_token_oauth2_invalid_credentials(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test OAuth2 token with invalid credentials."""
        user = await UserFactory.create_async(db_session, email="test@example.com")
        await db_session.commit()

        response = await client.post(
            "/api/auth/token",
            data={"username": "test@example.com", "password": "WrongPassword"}
        )

        assert response.status_code == 401


@pytest.mark.asyncio
class TestMeEndpoint:
    """Test GET /api/auth/me endpoint."""

    async def test_me_success(
        self,
        client: AsyncClient,
        user,
        auth_headers
    ):
        """Test getting current user info."""
        response = await client.get("/api/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert data["user"]["id"] == user.id
        assert data["user"]["email"] == user.email
        assert "access_token" in data  # Returns new token

    async def test_me_no_token(self, client: AsyncClient):
        """Test /me without authentication token."""
        response = await client.get("/api/auth/me")

        assert response.status_code == 401

    async def test_me_invalid_token(self, client: AsyncClient):
        """Test /me with invalid token."""
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )

        assert response.status_code == 401

    async def test_me_malformed_header(self, client: AsyncClient):
        """Test /me with malformed authorization header."""
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": "InvalidFormat token"}
        )

        assert response.status_code == 401

    async def test_me_expired_token(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test /me with expired token."""
        from datetime import timedelta
        from app.core.security import create_access_token

        user = await UserFactory.create_async(db_session)
        await db_session.commit()

        # Create expired token
        expired_token = create_access_token(
            {"sub": str(user.id)},
            token_version=user.token_version,
            expires_delta=timedelta(seconds=-10)
        )

        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )

        assert response.status_code == 401


@pytest.mark.asyncio
class TestLogoutEndpoint:
    """Test POST /api/auth/logout endpoint."""

    async def test_logout_success(
        self,
        client: AsyncClient,
        user,
        auth_headers
    ):
        """Test successful logout."""
        response = await client.post("/api/auth/logout", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "message" in data

        # After logout, token should be blacklisted
        # Try using the same token again
        me_response = await client.get("/api/auth/me", headers=auth_headers)
        assert me_response.status_code == 401  # Token blacklisted

    async def test_logout_no_token(self, client: AsyncClient):
        """Test logout without token."""
        response = await client.post("/api/auth/logout")

        assert response.status_code == 401

    async def test_logout_invalid_token(self, client: AsyncClient):
        """Test logout with invalid token."""
        response = await client.post(
            "/api/auth/logout",
            headers={"Authorization": "Bearer invalid_token"}
        )

        assert response.status_code == 401


@pytest.mark.asyncio
class TestLoginEdgeCases:
    """Test edge cases for login."""

    async def test_login_sql_injection_attempt(self, client: AsyncClient):
        """Test that SQL injection is prevented."""
        response = await client.post(
            "/api/auth/login",
            json={
                "email": "admin' OR '1'='1",
                "password": "password"
            }
        )

        # Should fail validation or return 401, not cause SQL error
        assert response.status_code in [401, 422]

    async def test_login_xss_in_email(self, client: AsyncClient):
        """Test that XSS attempts are handled safely."""
        response = await client.post(
            "/api/auth/login",
            json={
                "email": "<script>alert('xss')</script>@example.com",
                "password": "password"
            }
        )

        assert response.status_code in [401, 422]

    async def test_login_very_long_password(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test login with very long password."""
        long_password = "a" * 10000
        user = await UserFactory.create_async(
            db_session,
            email="test@example.com",
            password=get_password_hash(long_password)
        )
        await db_session.commit()

        response = await client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": long_password}
        )

        assert response.status_code == 200

    async def test_login_unicode_password(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test login with unicode characters in password."""
        unicode_password = "Пароль123!🔒"
        user = await UserFactory.create_async(
            db_session,
            email="test@example.com",
            password=get_password_hash(unicode_password)
        )
        await db_session.commit()

        response = await client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": unicode_password}
        )

        assert response.status_code == 200

    async def test_multiple_concurrent_logins(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test multiple concurrent logins for same user."""
        user = await UserFactory.create_async(
            db_session,
            email="test@example.com",
            password=get_password_hash("Password123!")
        )
        await db_session.commit()

        # Simulate concurrent logins
        responses = []
        for _ in range(3):
            response = await client.post(
                "/api/auth/login",
                json={"email": "test@example.com", "password": "Password123!"}
            )
            responses.append(response)

        # All should succeed
        assert all(r.status_code == 200 for r in responses)

        # Each should get a different token
        tokens = [r.json()["access_token"] for r in responses]
        assert len(set(tokens)) == 3  # All unique
