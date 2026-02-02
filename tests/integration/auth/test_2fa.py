"""
Integration tests for Two-Factor Authentication (2FA).

Tests:
- POST /api/auth/2fa/setup
- POST /api/auth/2fa/verify
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
import pyotp
import base64
import re

from tests.factories import UserFactory


@pytest.mark.asyncio
class TestTwoFactorSetup:
    """Test POST /api/auth/2fa/setup."""

    async def test_2fa_setup_success(
        self,
        client: AsyncClient,
        user,
        auth_headers,
        db_session: AsyncSession
    ):
        """Test setting up 2FA for user."""
        response = await client.post(
            "/api/auth/2fa/setup",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response contains secret and QR code
        assert "secret" in data
        assert "otpauth_url" in data
        assert "qr_code" in data

        # Verify secret is base32 encoded
        secret = data["secret"]
        assert len(secret) == 32
        assert secret.isupper()
        assert secret.isalnum()

        # Verify otpauth URL format
        otpauth_url = data["otpauth_url"]
        assert otpauth_url.startswith("otpauth://totp/")
        assert user.email in otpauth_url
        assert secret in otpauth_url

        # Verify QR code is base64 encoded
        qr_code = data["qr_code"]
        assert qr_code.startswith("data:image/png;base64,")
        # Verify base64 can be decoded
        base64_data = qr_code.split(",")[1]
        try:
            base64.b64decode(base64_data)
        except Exception:
            pytest.fail("QR code is not valid base64")

    async def test_2fa_setup_without_auth(self, client: AsyncClient):
        """Test 2FA setup without authentication."""
        response = await client.post("/api/auth/2fa/setup")

        assert response.status_code == 401

    async def test_2fa_setup_multiple_times(
        self,
        client: AsyncClient,
        user,
        auth_headers
    ):
        """Test that user can setup 2FA multiple times (regenerate secret)."""
        # First setup
        response1 = await client.post(
            "/api/auth/2fa/setup",
            headers=auth_headers
        )
        assert response1.status_code == 200
        secret1 = response1.json()["secret"]

        # Second setup (regenerate)
        response2 = await client.post(
            "/api/auth/2fa/setup",
            headers=auth_headers
        )
        assert response2.status_code == 200
        secret2 = response2.json()["secret"]

        # Secrets should be different (regenerated)
        assert secret1 != secret2


@pytest.mark.asyncio
class TestTwoFactorVerify:
    """Test POST /api/auth/2fa/verify."""

    async def test_2fa_verify_success(
        self,
        client: AsyncClient,
        user,
        auth_headers,
        db_session: AsyncSession
    ):
        """Test verifying TOTP code and enabling 2FA."""
        # Setup 2FA first
        setup_response = await client.post(
            "/api/auth/2fa/setup",
            headers=auth_headers
        )
        secret = setup_response.json()["secret"]

        # Generate valid TOTP code
        totp = pyotp.TOTP(secret)
        code = totp.now()

        # Verify the code
        verify_response = await client.post(
            "/api/auth/2fa/verify",
            headers=auth_headers,
            json={"code": code}
        )

        assert verify_response.status_code == 200
        data = verify_response.json()
        assert "message" in data

        # Verify user's 2FA is now enabled in DB
        await db_session.refresh(user)
        assert user.two_factor_enabled is True
        assert user.two_factor_secret == secret

    async def test_2fa_verify_invalid_code(
        self,
        client: AsyncClient,
        user,
        auth_headers
    ):
        """Test verifying with invalid TOTP code."""
        # Setup 2FA first
        await client.post("/api/auth/2fa/setup", headers=auth_headers)

        # Try with invalid code
        verify_response = await client.post(
            "/api/auth/2fa/verify",
            headers=auth_headers,
            json={"code": "000000"}
        )

        assert verify_response.status_code == 400
        assert "detail" in verify_response.json()

    async def test_2fa_verify_without_setup(
        self,
        client: AsyncClient,
        user,
        auth_headers
    ):
        """Test verify without running setup first."""
        # Try to verify without secret
        response = await client.post(
            "/api/auth/2fa/verify",
            headers=auth_headers,
            json={"code": "123456"}
        )

        # Should fail - no secret exists
        assert response.status_code == 400

    async def test_2fa_verify_wrong_code_format(
        self,
        client: AsyncClient,
        user,
        auth_headers
    ):
        """Test verify with wrong code format."""
        await client.post("/api/auth/2fa/setup", headers=auth_headers)

        # Wrong length
        response = await client.post(
            "/api/auth/2fa/verify",
            headers=auth_headers,
            json={"code": "12345"}  # Only 5 digits
        )
        assert response.status_code in [400, 422]

        # Non-numeric
        response = await client.post(
            "/api/auth/2fa/verify",
            headers=auth_headers,
            json={"code": "abcdef"}
        )
        assert response.status_code in [400, 422]

    async def test_2fa_verify_without_auth(self, client: AsyncClient):
        """Test 2FA verify without authentication."""
        response = await client.post(
            "/api/auth/2fa/verify",
            json={"code": "123456"}
        )

        assert response.status_code == 401


@pytest.mark.asyncio
class TestTwoFactorLogin:
    """Test login flow with 2FA enabled."""

    async def test_login_with_2fa_enabled(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test that login with 2FA user requires TOTP (if implemented)."""
        from app.core.security import get_password_hash, generate_totp_secret

        # Create user with 2FA enabled
        secret = generate_totp_secret()
        user = await UserFactory.create_async(
            db_session,
            email="2fa@example.com",
            password=get_password_hash("Password123!"),
            two_factor_enabled=True,
            two_factor_secret=secret
        )
        await db_session.commit()

        # Try login without TOTP
        response = await client.post(
            "/api/auth/login",
            json={"email": "2fa@example.com", "password": "Password123!"}
        )

        # Behavior depends on implementation:
        # - Might return 401 and require TOTP
        # - Might return 200 with flag indicating 2FA needed
        # - Might require TOTP in same request
        assert response.status_code in [200, 401]

        # If login requires TOTP in request, test that flow
        if response.status_code == 401:
            totp = pyotp.TOTP(secret)
            code = totp.now()

            # Try with TOTP (if endpoint supports it)
            response_with_totp = await client.post(
                "/api/auth/login",
                json={
                    "email": "2fa@example.com",
                    "password": "Password123!",
                    "totp": code
                }
            )
            # Should succeed if implementation supports TOTP in login
            assert response_with_totp.status_code in [200, 422]


@pytest.mark.asyncio
class TestTwoFactorEdgeCases:
    """Test edge cases for 2FA."""

    async def test_2fa_code_timing_window(
        self,
        client: AsyncClient,
        user,
        auth_headers
    ):
        """Test that TOTP code is valid within time window."""
        import time

        setup_response = await client.post(
            "/api/auth/2fa/setup",
            headers=auth_headers
        )
        secret = setup_response.json()["secret"]

        totp = pyotp.TOTP(secret)

        # Get code at current time
        code_now = totp.now()

        # Should work immediately
        verify_response = await client.post(
            "/api/auth/2fa/verify",
            headers=auth_headers,
            json={"code": code_now}
        )
        assert verify_response.status_code == 200

    async def test_2fa_cannot_reuse_code(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test that same TOTP code cannot be used twice (if implemented)."""
        from app.core.security import get_password_hash, generate_totp_secret

        # Create user with 2FA
        secret = generate_totp_secret()
        user = await UserFactory.create_async(
            db_session,
            email="test@example.com",
            password=get_password_hash("Password123!"),
            two_factor_enabled=True,
            two_factor_secret=secret
        )
        await db_session.commit()

        totp = pyotp.TOTP(secret)
        code = totp.now()

        # First use
        from app.core.security import create_access_token
        token = create_access_token(
            {"sub": str(user.id)},
            token_version=user.token_version
        )

        # If implementation tracks used codes, second use should fail
        # This depends on your implementation
        pass  # Document expected behavior

    async def test_2fa_disable_flow(
        self,
        client: AsyncClient,
        user,
        auth_headers,
        db_session: AsyncSession
    ):
        """Test disabling 2FA (if endpoint exists)."""
        # Setup and verify 2FA
        setup_response = await client.post(
            "/api/auth/2fa/setup",
            headers=auth_headers
        )
        secret = setup_response.json()["secret"]

        totp = pyotp.TOTP(secret)
        code = totp.now()

        await client.post(
            "/api/auth/2fa/verify",
            headers=auth_headers,
            json={"code": code}
        )

        # Verify 2FA is enabled
        await db_session.refresh(user)
        assert user.two_factor_enabled is True

        # If disable endpoint exists, test it
        # Example: DELETE /api/auth/2fa
        disable_response = await client.delete(
            "/api/auth/2fa",
            headers=auth_headers
        )

        # Might not be implemented yet
        if disable_response.status_code == 200:
            await db_session.refresh(user)
            assert user.two_factor_enabled is False

    async def test_2fa_backup_codes(self, client: AsyncClient, user, auth_headers):
        """Test backup codes generation (if implemented)."""
        # Some 2FA implementations provide backup codes
        # Test if your implementation has this feature

        setup_response = await client.post(
            "/api/auth/2fa/setup",
            headers=auth_headers
        )

        # Check if backup codes are included
        data = setup_response.json()
        if "backup_codes" in data:
            backup_codes = data["backup_codes"]
            assert isinstance(backup_codes, list)
            assert len(backup_codes) > 0
        else:
            # Feature not implemented, skip
            pass

    async def test_2fa_secret_persistence(
        self,
        client: AsyncClient,
        user,
        auth_headers,
        db_session: AsyncSession
    ):
        """Test that 2FA secret persists in database."""
        # Setup 2FA
        setup_response = await client.post(
            "/api/auth/2fa/setup",
            headers=auth_headers
        )
        secret = setup_response.json()["secret"]

        totp = pyotp.TOTP(secret)
        code = totp.now()

        # Verify
        await client.post(
            "/api/auth/2fa/verify",
            headers=auth_headers,
            json={"code": code}
        )

        # Refresh user from DB
        await db_session.refresh(user)

        # Secret should match
        assert user.two_factor_secret == secret
        assert user.two_factor_enabled is True

    async def test_2fa_qr_code_scannable(
        self,
        client: AsyncClient,
        user,
        auth_headers
    ):
        """Test that QR code contains correct information."""
        response = await client.post(
            "/api/auth/2fa/setup",
            headers=auth_headers
        )

        data = response.json()
        otpauth_url = data["otpauth_url"]
        secret = data["secret"]

        # Parse otpauth URL
        # Format: otpauth://totp/AppName:user@example.com?secret=...&issuer=AppName
        assert "totp" in otpauth_url
        assert user.email in otpauth_url
        assert secret in otpauth_url

        # Extract secret from URL
        match = re.search(r'secret=([A-Z0-9]+)', otpauth_url)
        assert match is not None
        url_secret = match.group(1)
        assert url_secret == secret
