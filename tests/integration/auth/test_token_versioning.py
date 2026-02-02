"""
Integration tests for token versioning.

Tests that token_version is incremented and old tokens are invalidated
when sensitive operations occur (password change, etc.).
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, create_access_token
from tests.factories import UserFactory


@pytest.mark.asyncio
class TestTokenVersioning:
    """Test token version invalidation."""

    async def test_token_version_starts_at_one(
        self,
        db_session: AsyncSession
    ):
        """Test that new users start with token_version = 1."""
        user = await UserFactory.create_async(db_session)
        await db_session.commit()

        assert user.token_version == 1

    async def test_old_token_invalid_after_password_change(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test that tokens are invalidated after password change."""
        from app.core.security import create_access_token

        # Create user
        user = await UserFactory.create_async(
            db_session,
            email="test@example.com",
            password=get_password_hash("OldPassword123!")
        )
        await db_session.commit()

        # Create token with version 1
        old_token = create_access_token(
            {"sub": str(user.id)},
            token_version=1
        )

        # Verify token works
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {old_token}"}
        )
        assert response.status_code == 200

        # Change password (simulating forgot password flow)
        # This should increment token_version to 2
        reset_token = create_access_token(
            {"sub": str(user.id), "purpose": "password_reset"},
            token_version=user.token_version
        )

        await client.post(
            "/api/auth/forgot-password/confirm",
            headers={"Authorization": f"Bearer {reset_token}"},
            json={"new_password": "NewPassword456!"}
        )

        # Refresh user from DB
        await db_session.refresh(user)
        assert user.token_version == 2

        # Old token should now be invalid
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {old_token}"}
        )
        assert response.status_code == 401

    async def test_new_token_works_after_password_change(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test that new tokens work after password change."""
        user = await UserFactory.create_async(
            db_session,
            email="test@example.com",
            password=get_password_hash("OldPassword123!")
        )
        await db_session.commit()

        # Change password
        reset_token = create_access_token(
            {"sub": str(user.id), "purpose": "password_reset"},
            token_version=user.token_version
        )

        await client.post(
            "/api/auth/forgot-password/confirm",
            headers={"Authorization": f"Bearer {reset_token}"},
            json={"new_password": "NewPassword456!"}
        )

        # Login with new password should work
        login_response = await client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "NewPassword456!"}
        )
        assert login_response.status_code == 200

        new_token = login_response.json()["access_token"]

        # New token should work
        me_response = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {new_token}"}
        )
        assert me_response.status_code == 200

    async def test_token_version_in_jwt_payload(
        self,
        db_session: AsyncSession
    ):
        """Test that token_version is included in JWT payload."""
        from jose import jwt
        from app.core.security import SECRET_KEY, ALGORITHM

        user = await UserFactory.create_async(db_session)
        await db_session.commit()

        token = create_access_token(
            {"sub": str(user.id)},
            token_version=user.token_version
        )

        # Decode token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        assert "tv" in payload
        assert payload["tv"] == user.token_version

    async def test_multiple_password_changes_increment_version(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test that each password change increments token_version."""
        user = await UserFactory.create_async(
            db_session,
            email="test@example.com",
            password=get_password_hash("Password1!")
        )
        await db_session.commit()

        initial_version = user.token_version
        assert initial_version == 1

        # Change password 3 times
        for i in range(3):
            reset_token = create_access_token(
                {"sub": str(user.id), "purpose": "password_reset"},
                token_version=user.token_version
            )

            await client.post(
                "/api/auth/forgot-password/confirm",
                headers={"Authorization": f"Bearer {reset_token}"},
                json={"new_password": f"NewPassword{i}!"}
            )

            await db_session.refresh(user)
            expected_version = initial_version + i + 1
            assert user.token_version == expected_version

    async def test_concurrent_token_version_updates(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test that concurrent password changes handle token_version correctly."""
        import asyncio

        user = await UserFactory.create_async(
            db_session,
            email="test@example.com",
            password=get_password_hash("Password123!")
        )
        await db_session.commit()

        initial_version = user.token_version

        # Try to change password concurrently
        async def change_password(new_pass):
            reset_token = create_access_token(
                {"sub": str(user.id), "purpose": "password_reset"},
                token_version=user.token_version
            )

            return await client.post(
                "/api/auth/forgot-password/confirm",
                headers={"Authorization": f"Bearer {reset_token}"},
                json={"new_password": new_pass}
            )

        responses = await asyncio.gather(
            change_password("NewPass1!"),
            change_password("NewPass2!"),
            change_password("NewPass3!"),
            return_exceptions=True
        )

        # At least one should succeed
        success_count = sum(
            1 for r in responses
            if not isinstance(r, Exception) and r.status_code == 204
        )
        assert success_count >= 1

        # Final version should be initial + number of successful changes
        await db_session.refresh(user)
        assert user.token_version > initial_version


@pytest.mark.asyncio
class TestTokenVersionEdgeCases:
    """Test edge cases for token versioning."""

    async def test_token_with_wrong_version_fails(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test that token with wrong version is rejected."""
        user = await UserFactory.create_async(db_session)
        await db_session.commit()

        # Create token with wrong version
        wrong_token = create_access_token(
            {"sub": str(user.id)},
            token_version=999  # Wrong version
        )

        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {wrong_token}"}
        )

        assert response.status_code == 401

    async def test_token_without_version_fails(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test that token without tv field is rejected."""
        from jose import jwt
        from app.core.security import SECRET_KEY, ALGORITHM

        user = await UserFactory.create_async(db_session)
        await db_session.commit()

        # Create token without tv field
        payload = {"sub": str(user.id)}
        token_without_tv = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token_without_tv}"}
        )

        # Should fail validation
        assert response.status_code == 401

    async def test_logout_does_not_increment_version(
        self,
        client: AsyncClient,
        user,
        auth_headers,
        db_session: AsyncSession
    ):
        """Test that logout does not increment token_version."""
        initial_version = user.token_version

        # Logout
        await client.post("/api/auth/logout", headers=auth_headers)

        # Verify version unchanged
        await db_session.refresh(user)
        assert user.token_version == initial_version

    async def test_regular_api_calls_do_not_increment_version(
        self,
        client: AsyncClient,
        user,
        auth_headers,
        db_session: AsyncSession
    ):
        """Test that normal API calls don't increment token_version."""
        initial_version = user.token_version

        # Make multiple API calls
        for _ in range(5):
            await client.get("/api/auth/me", headers=auth_headers)

        # Version should remain unchanged
        await db_session.refresh(user)
        assert user.token_version == initial_version

    async def test_login_uses_current_token_version(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test that login creates token with current token_version."""
        from jose import jwt
        from app.core.security import SECRET_KEY, ALGORITHM

        user = await UserFactory.create_async(
            db_session,
            email="test@example.com",
            password=get_password_hash("Password123!")
        )
        await db_session.commit()

        # Login
        login_response = await client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "Password123!"}
        )

        token = login_response.json()["access_token"]

        # Decode and verify version
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["tv"] == user.token_version

    async def test_me_endpoint_returns_new_token_with_same_version(
        self,
        client: AsyncClient,
        user,
        auth_headers
    ):
        """Test that /me returns new token with same version."""
        from jose import jwt
        from app.core.security import SECRET_KEY, ALGORITHM

        response = await client.get("/api/auth/me", headers=auth_headers)

        assert response.status_code == 200
        new_token = response.json()["access_token"]

        # New token should have same version as user
        payload = jwt.decode(new_token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["tv"] == user.token_version

    async def test_token_version_overflow_handling(
        self,
        db_session: AsyncSession
    ):
        """Test token_version with very large values."""
        # Create user with very high token version
        user = await UserFactory.create_async(
            db_session,
            token_version=2147483647  # Max int32
        )
        await db_session.commit()

        # Should be able to create token
        token = create_access_token(
            {"sub": str(user.id)},
            token_version=user.token_version
        )

        assert token is not None

    async def test_different_users_have_independent_versions(
        self,
        db_session: AsyncSession
    ):
        """Test that each user has independent token_version."""
        user1 = await UserFactory.create_async(db_session, email="user1@test.com")
        user2 = await UserFactory.create_async(db_session, email="user2@test.com")
        await db_session.commit()

        # Both should start at 1
        assert user1.token_version == 1
        assert user2.token_version == 1

        # Manually increment user1's version
        user1.token_version = 5
        await db_session.commit()

        # user2's version should be unaffected
        await db_session.refresh(user2)
        assert user2.token_version == 1
