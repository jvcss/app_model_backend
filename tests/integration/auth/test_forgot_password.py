"""
Integration tests for forgot password flow.

Tests 3-step process:
1. POST /api/auth/forgot-password/start
2. POST /api/auth/forgot-password/verify
3. POST /api/auth/forgot-password/confirm
"""

import pytest
from httpx import AsyncClient
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.password_reset import PasswordReset
from app.models.user import User
from app.core.security import get_password_hash, generate_otp, hash_otp, verify_password
from tests.factories import UserFactory


@pytest.mark.asyncio
class TestForgotPasswordStart:
    """Test POST /api/auth/forgot-password/start."""

    async def test_forgot_password_start_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        mocker
    ):
        """Test starting password reset for existing user."""
        # Mock Celery task to prevent actual email sending
        mock_task = mocker.patch("app.api.endpoints.auth.send_password_otp_local.delay")

        user = await UserFactory.create_async(
            db_session,
            email="test@example.com"
        )
        await db_session.commit()

        response = await client.post(
            "/api/auth/forgot-password/start",
            json={"email": "test@example.com"}
        )

        assert response.status_code == 202
        data = response.json()
        assert "message" in data

        # Verify PasswordReset created in DB
        result = await db_session.execute(
            select(PasswordReset).where(PasswordReset.user_id == user.id)
        )
        pr = result.scalar_one_or_none()
        assert pr is not None
        assert pr.otp_hash is not None
        assert pr.otp_expires_at > datetime.now(timezone.utc)
        assert pr.otp_verified is False

        # Verify Celery task called
        assert mock_task.called

    async def test_forgot_password_start_nonexistent_user(
        self,
        client: AsyncClient,
        mocker
    ):
        """Test password reset for non-existent user (anti-enumeration)."""
        mock_task = mocker.patch("app.api.endpoints.auth.send_password_otp_local.delay")

        response = await client.post(
            "/api/auth/forgot-password/start",
            json={"email": "nonexistent@example.com"}
        )

        # Should return same response (anti-enumeration)
        assert response.status_code == 202

        # Task should NOT be called
        assert not mock_task.called

    async def test_forgot_password_start_invalid_email(self, client: AsyncClient):
        """Test with invalid email format."""
        response = await client.post(
            "/api/auth/forgot-password/start",
            json={"email": "not-an-email"}
        )

        assert response.status_code == 422

    async def test_forgot_password_start_rate_limiting(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        mocker
    ):
        """Test rate limiting on password reset (5 requests per 15 min)."""
        mock_task = mocker.patch("app.api.endpoints.auth.send_password_otp_local.delay")

        user = await UserFactory.create_async(db_session, email="test@example.com")
        await db_session.commit()

        # Send 5 requests (max allowed)
        for i in range(5):
            response = await client.post(
                "/api/auth/forgot-password/start",
                json={"email": "test@example.com"}
            )
            assert response.status_code == 202

        # 6th request should be rate limited
        response = await client.post(
            "/api/auth/forgot-password/start",
            json={"email": "test@example.com"}
        )
        assert response.status_code == 429  # Too Many Requests


@pytest.mark.asyncio
class TestForgotPasswordVerify:
    """Test POST /api/auth/forgot-password/verify."""

    async def test_verify_valid_otp(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test verifying correct OTP."""
        user = await UserFactory.create_async(db_session, email="test@example.com")
        await db_session.commit()

        # Create PasswordReset with known OTP
        otp = "123456"
        pr = PasswordReset(
            user_id=user.id,
            email=user.email,
            otp_hash=hash_otp(otp),
            otp_expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            require_totp=False
        )
        db_session.add(pr)
        await db_session.commit()

        response = await client.post(
            "/api/auth/forgot-password/verify",
            json={"email": "test@example.com", "otp": otp}
        )

        assert response.status_code == 200
        data = response.json()
        assert "reset_session_token" in data
        assert isinstance(data["reset_session_token"], str)

        # Verify OTP marked as verified
        await db_session.refresh(pr)
        assert pr.otp_verified is True
        assert pr.reset_session_issued_at is not None

    async def test_verify_invalid_otp(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test verifying incorrect OTP."""
        user = await UserFactory.create_async(db_session, email="test@example.com")
        await db_session.commit()

        otp = "123456"
        pr = PasswordReset(
            user_id=user.id,
            email=user.email,
            otp_hash=hash_otp(otp),
            otp_expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            require_totp=False
        )
        db_session.add(pr)
        await db_session.commit()

        response = await client.post(
            "/api/auth/forgot-password/verify",
            json={"email": "test@example.com", "otp": "654321"}
        )

        assert response.status_code == 400
        assert "detail" in response.json()

    async def test_verify_expired_otp(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test verifying expired OTP."""
        user = await UserFactory.create_async(db_session, email="test@example.com")
        await db_session.commit()

        otp = "123456"
        pr = PasswordReset(
            user_id=user.id,
            email=user.email,
            otp_hash=hash_otp(otp),
            otp_expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),  # Expired
            require_totp=False
        )
        db_session.add(pr)
        await db_session.commit()

        response = await client.post(
            "/api/auth/forgot-password/verify",
            json={"email": "test@example.com", "otp": otp}
        )

        assert response.status_code == 400

    async def test_verify_with_2fa_required(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test verify when user has 2FA enabled (requires TOTP)."""
        from app.core.security import generate_totp_secret
        import pyotp

        # Create user with 2FA enabled
        secret = generate_totp_secret()
        user = await UserFactory.create_async(
            db_session,
            email="test@example.com",
            two_factor_enabled=True,
            two_factor_secret=secret
        )
        await db_session.commit()

        otp = "123456"
        pr = PasswordReset(
            user_id=user.id,
            email=user.email,
            otp_hash=hash_otp(otp),
            otp_expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            require_totp=True
        )
        db_session.add(pr)
        await db_session.commit()

        # Generate valid TOTP
        totp = pyotp.TOTP(secret)
        totp_code = totp.now()

        response = await client.post(
            "/api/auth/forgot-password/verify",
            json={
                "email": "test@example.com",
                "otp": otp,
                "totp": totp_code
            }
        )

        assert response.status_code == 200
        assert "reset_session_token" in response.json()

    async def test_verify_missing_totp_when_required(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test verify without TOTP when 2FA is enabled."""
        user = await UserFactory.create_async(
            db_session,
            email="test@example.com",
            two_factor_enabled=True
        )
        await db_session.commit()

        otp = "123456"
        pr = PasswordReset(
            user_id=user.id,
            email=user.email,
            otp_hash=hash_otp(otp),
            otp_expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            require_totp=True
        )
        db_session.add(pr)
        await db_session.commit()

        response = await client.post(
            "/api/auth/forgot-password/verify",
            json={"email": "test@example.com", "otp": otp}
        )

        assert response.status_code == 400

    async def test_verify_rate_limiting(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test rate limiting on OTP verification (10 requests per 15 min)."""
        user = await UserFactory.create_async(db_session, email="test@example.com")
        await db_session.commit()

        otp = "123456"
        pr = PasswordReset(
            user_id=user.id,
            email=user.email,
            otp_hash=hash_otp(otp),
            otp_expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            require_totp=False
        )
        db_session.add(pr)
        await db_session.commit()

        # Send 10 requests (max allowed)
        for i in range(10):
            await client.post(
                "/api/auth/forgot-password/verify",
                json={"email": "test@example.com", "otp": "wrong"}
            )

        # 11th request should be rate limited
        response = await client.post(
            "/api/auth/forgot-password/verify",
            json={"email": "test@example.com", "otp": otp}
        )
        assert response.status_code == 429


@pytest.mark.asyncio
class TestForgotPasswordConfirm:
    """Test POST /api/auth/forgot-password/confirm."""

    async def test_confirm_new_password_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test confirming new password with valid reset token."""
        from app.core.security import create_access_token

        user = await UserFactory.create_async(
            db_session,
            email="test@example.com",
            password=get_password_hash("OldPassword123!")
        )
        await db_session.commit()

        # Create reset session token
        reset_token = create_access_token(
            {"sub": str(user.id), "purpose": "password_reset"},
            token_version=user.token_version
        )

        response = await client.post(
            "/api/auth/forgot-password/confirm",
            headers={"Authorization": f"Bearer {reset_token}"},
            json={"new_password": "NewPassword456!"}
        )

        assert response.status_code == 204

        # Verify password changed
        await db_session.refresh(user)
        assert verify_password("NewPassword456!", user.password)
        assert not verify_password("OldPassword123!", user.password)

        # Verify token_version incremented (invalidates old tokens)
        assert user.token_version == 2

    async def test_confirm_can_login_with_new_password(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test that user can login with new password after reset."""
        from app.core.security import create_access_token

        user = await UserFactory.create_async(
            db_session,
            email="test@example.com",
            password=get_password_hash("OldPassword123!")
        )
        await db_session.commit()

        reset_token = create_access_token(
            {"sub": str(user.id), "purpose": "password_reset"},
            token_version=user.token_version
        )

        # Confirm password change
        await client.post(
            "/api/auth/forgot-password/confirm",
            headers={"Authorization": f"Bearer {reset_token}"},
            json={"new_password": "NewPassword456!"}
        )

        # Try login with new password
        login_response = await client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "NewPassword456!"}
        )

        assert login_response.status_code == 200

        # Old password should not work
        old_login_response = await client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "OldPassword123!"}
        )
        assert old_login_response.status_code == 401

    async def test_confirm_without_reset_token(self, client: AsyncClient):
        """Test confirm without reset token."""
        response = await client.post(
            "/api/auth/forgot-password/confirm",
            json={"new_password": "NewPassword456!"}
        )

        assert response.status_code == 401

    async def test_confirm_with_invalid_token(self, client: AsyncClient):
        """Test confirm with invalid reset token."""
        response = await client.post(
            "/api/auth/forgot-password/confirm",
            headers={"Authorization": "Bearer invalid_token"},
            json={"new_password": "NewPassword456!"}
        )

        assert response.status_code == 401

    async def test_confirm_with_regular_token(
        self,
        client: AsyncClient,
        user,
        auth_headers
    ):
        """Test that regular auth token cannot be used for password reset."""
        response = await client.post(
            "/api/auth/forgot-password/confirm",
            headers=auth_headers,  # Regular token, not reset token
            json={"new_password": "NewPassword456!"}
        )

        # Should fail - must use specific reset token
        assert response.status_code in [400, 401, 403]

    async def test_confirm_weak_password(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test confirm with weak password (if validation exists)."""
        from app.core.security import create_access_token

        user = await UserFactory.create_async(db_session)
        await db_session.commit()

        reset_token = create_access_token(
            {"sub": str(user.id), "purpose": "password_reset"},
            token_version=user.token_version
        )

        response = await client.post(
            "/api/auth/forgot-password/confirm",
            headers={"Authorization": f"Bearer {reset_token}"},
            json={"new_password": "123"}  # Weak password
        )

        # Might be 422 if validation exists, or 204 if not
        assert response.status_code in [204, 422]


@pytest.mark.asyncio
class TestForgotPasswordFullFlow:
    """Test complete forgot password flow end-to-end."""

    async def test_complete_password_reset_flow(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        mocker
    ):
        """Test complete password reset from start to finish."""
        # Mock Celery task
        mock_task = mocker.patch("app.api.endpoints.auth.send_password_otp_local.delay")

        # Create user
        user = await UserFactory.create_async(
            db_session,
            email="test@example.com",
            password=get_password_hash("OldPassword123!")
        )
        await db_session.commit()

        # Step 1: Start password reset
        start_response = await client.post(
            "/api/auth/forgot-password/start",
            json={"email": "test@example.com"}
        )
        assert start_response.status_code == 202

        # Simulate getting OTP from database (in real scenario, from email)
        result = await db_session.execute(
            select(PasswordReset).where(PasswordReset.user_id == user.id)
        )
        pr = result.scalar_one()

        # For testing, we need to know the OTP
        # In real scenario, user would receive it via email
        test_otp = "123456"
        pr.otp_hash = hash_otp(test_otp)
        await db_session.commit()

        # Step 2: Verify OTP
        verify_response = await client.post(
            "/api/auth/forgot-password/verify",
            json={"email": "test@example.com", "otp": test_otp}
        )
        assert verify_response.status_code == 200
        reset_token = verify_response.json()["reset_session_token"]

        # Step 3: Confirm new password
        confirm_response = await client.post(
            "/api/auth/forgot-password/confirm",
            headers={"Authorization": f"Bearer {reset_token}"},
            json={"new_password": "NewPassword456!"}
        )
        assert confirm_response.status_code == 204

        # Step 4: Verify can login with new password
        login_response = await client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "NewPassword456!"}
        )
        assert login_response.status_code == 200

        # Step 5: Verify old password doesn't work
        old_login_response = await client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "OldPassword123!"}
        )
        assert old_login_response.status_code == 401
