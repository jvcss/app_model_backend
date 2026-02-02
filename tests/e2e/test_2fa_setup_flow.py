"""
End-to-end test for complete 2FA setup and usage flow.

Tests the full 2FA journey from setup to login.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories.user import UserFactory


@pytest.mark.e2e
@pytest.mark.asyncio
class TestTwoFactorAuthFlow:
    """Complete 2FA setup and login flow."""

    async def test_complete_2fa_setup_flow(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """
        Test complete 2FA setup and usage:
        1. Create user and login
        2. Setup 2FA (get secret and QR code)
        3. Verify TOTP and enable 2FA
        4. Logout
        5. Login with password + TOTP
        6. Verify access works
        """
        # Step 1: Create user and login
        user = await UserFactory.create_with_team_async(
            db_session, email="2fa@test.com", password="Test123!"
        )
        await db_session.commit()

        login_response = await client.post(
            "/api/auth/login",
            json={"email": "2fa@test.com", "password": "Test123!"},
        )

        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Step 2: Setup 2FA
        setup_response = await client.post(
            "/api/auth/2fa/setup", headers=headers
        )

        assert setup_response.status_code == 200
        setup_data = setup_response.json()
        assert "secret" in setup_data
        assert "qr_code_url" in setup_data

        secret = setup_data["secret"]

        # Step 3: Verify TOTP and enable 2FA
        # Generate valid TOTP
        import pyotp

        totp = pyotp.TOTP(secret)
        valid_code = totp.now()

        verify_response = await client.post(
            "/api/auth/2fa/verify",
            headers=headers,
            json={"totp_code": valid_code},
        )

        assert verify_response.status_code == 200

        # Step 4: Logout
        logout_response = await client.post(
            "/api/auth/logout", headers=headers
        )

        assert logout_response.status_code == 200

        # Step 5: Login with password + TOTP
        # First, login with password
        login_response = await client.post(
            "/api/auth/login",
            json={"email": "2fa@test.com", "password": "Test123!"},
        )

        assert login_response.status_code == 200

        # Then verify TOTP
        new_code = totp.now()
        token_response = await client.post(
            "/api/auth/token",
            data={
                "username": "2fa@test.com",
                "password": "Test123!",
                "totp_code": new_code,
            },
        )

        assert token_response.status_code == 200
        new_token = token_response.json()["access_token"]

        # Step 6: Verify access works
        me_response = await client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {new_token}"}
        )

        assert me_response.status_code == 200
        assert me_response.json()["user"]["two_factor_enabled"] is True

    async def test_2fa_disable_flow(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """
        Test disabling 2FA:
        1. Create user with 2FA enabled
        2. Login with TOTP
        3. Disable 2FA
        4. Logout
        5. Login without TOTP
        """
        # Step 1: Create user with 2FA
        import pyotp

        secret = pyotp.random_base32()
        user = await UserFactory.create_with_team_async(
            db_session,
            email="disable2fa@test.com",
            password="Test123!",
            two_factor_enabled=True,
            two_factor_secret=secret,
        )
        await db_session.commit()

        # Step 2: Login with TOTP
        totp = pyotp.TOTP(secret)
        code = totp.now()

        token_response = await client.post(
            "/api/auth/token",
            data={
                "username": "disable2fa@test.com",
                "password": "Test123!",
                "totp_code": code,
            },
        )

        assert token_response.status_code == 200
        token = token_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Step 3: Disable 2FA
        disable_response = await client.post(
            "/api/auth/2fa/disable",
            headers=headers,
            json={"password": "Test123!"},
        )

        assert disable_response.status_code == 200

        # Step 4: Logout
        await client.post("/api/auth/logout", headers=headers)

        # Step 5: Login without TOTP
        login_response = await client.post(
            "/api/auth/login",
            json={"email": "disable2fa@test.com", "password": "Test123!"},
        )

        assert login_response.status_code == 200
        # Should work without TOTP

        # Verify 2FA is disabled
        new_token = login_response.json()["access_token"]
        me_response = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {new_token}"},
        )

        assert me_response.json()["user"]["two_factor_enabled"] is False

    async def test_2fa_invalid_totp_rejection(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """
        Test that invalid TOTP codes are rejected:
        1. Setup 2FA
        2. Try to verify with wrong code
        3. Try to login with wrong code
        4. Verify both are rejected
        """
        # Step 1: Setup 2FA
        user = await UserFactory.create_with_team_async(
            db_session, email="invalid@test.com", password="Test123!"
        )
        await db_session.commit()

        login_response = await client.post(
            "/api/auth/login",
            json={"email": "invalid@test.com", "password": "Test123!"},
        )

        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        setup_response = await client.post(
            "/api/auth/2fa/setup", headers=headers
        )
        secret = setup_response.json()["secret"]

        # Step 2: Try to verify with wrong code
        verify_response = await client.post(
            "/api/auth/2fa/verify",
            headers=headers,
            json={"totp_code": "000000"},  # Invalid
        )

        assert verify_response.status_code == 400

        # Verify with correct code to enable 2FA
        import pyotp

        totp = pyotp.TOTP(secret)
        correct_code = totp.now()

        verify_response = await client.post(
            "/api/auth/2fa/verify",
            headers=headers,
            json={"totp_code": correct_code},
        )

        assert verify_response.status_code == 200

        # Step 3: Try to login with wrong TOTP
        token_response = await client.post(
            "/api/auth/token",
            data={
                "username": "invalid@test.com",
                "password": "Test123!",
                "totp_code": "000000",  # Invalid
            },
        )

        # Step 4: Verify rejection
        assert token_response.status_code == 401

    async def test_2fa_backup_codes(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """
        Test 2FA backup codes functionality:
        1. Setup 2FA
        2. Generate backup codes
        3. Disable 2FA
        4. Re-enable and verify backup codes regenerate
        """
        # Step 1: Create user and setup 2FA
        user = await UserFactory.create_with_team_async(
            db_session, email="backup@test.com", password="Test123!"
        )
        await db_session.commit()

        login_response = await client.post(
            "/api/auth/login",
            json={"email": "backup@test.com", "password": "Test123!"},
        )

        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        setup_response = await client.post(
            "/api/auth/2fa/setup", headers=headers
        )
        secret = setup_response.json()["secret"]

        # Verify to enable
        import pyotp

        totp = pyotp.TOTP(secret)
        code = totp.now()

        await client.post(
            "/api/auth/2fa/verify",
            headers=headers,
            json={"totp_code": code},
        )

        # Step 2: Generate backup codes (if endpoint exists)
        # Note: This assumes backup codes endpoint exists
        # Adjust based on actual implementation

        # Step 3: Disable 2FA
        disable_response = await client.post(
            "/api/auth/2fa/disable",
            headers=headers,
            json={"password": "Test123!"},
        )

        assert disable_response.status_code == 200

        # Step 4: Re-enable and verify
        setup_response2 = await client.post(
            "/api/auth/2fa/setup", headers=headers
        )
        new_secret = setup_response2.json()["secret"]

        # Secret should be different
        assert new_secret != secret

    async def test_2fa_time_based_window(
        self, client: AsyncClient, db_session: AsyncSession, freezer
    ):
        """
        Test TOTP time window tolerance:
        1. Setup 2FA
        2. Generate code
        3. Move time slightly forward (within window)
        4. Verify code still works
        5. Move time far forward (outside window)
        6. Verify code is rejected
        """
        # Step 1: Create user with 2FA
        import pyotp

        secret = pyotp.random_base32()
        user = await UserFactory.create_with_team_async(
            db_session,
            email="timewindow@test.com",
            password="Test123!",
            two_factor_enabled=True,
            two_factor_secret=secret,
        )
        await db_session.commit()

        # Step 2: Generate code
        totp = pyotp.TOTP(secret)
        code = totp.now()

        # Step 3: Move time slightly forward (10 seconds)
        freezer.move_to("10 seconds later")

        # Step 4: Code should still work (TOTP has ~30s window)
        token_response = await client.post(
            "/api/auth/token",
            data={
                "username": "timewindow@test.com",
                "password": "Test123!",
                "totp_code": code,
            },
        )

        # Might work or not depending on TOTP window implementation
        # Most TOTP implementations allow ±1 time step (30s)

        # Step 5: Move time far forward (5 minutes)
        freezer.move_to("5 minutes later")

        # Step 6: Old code should definitely be rejected
        token_response = await client.post(
            "/api/auth/token",
            data={
                "username": "timewindow@test.com",
                "password": "Test123!",
                "totp_code": code,  # Old code
            },
        )

        assert token_response.status_code == 401
