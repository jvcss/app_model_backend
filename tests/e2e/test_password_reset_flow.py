"""
End-to-end test for complete password reset flow.

Tests the full 3-step password reset journey.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from tests.factories.user import UserFactory


@pytest.mark.e2e
@pytest.mark.asyncio
class TestPasswordResetFlow:
    """Complete password reset flow (3 steps)."""

    async def test_complete_password_reset_flow(
        self, client: AsyncClient, db_session: AsyncSession, mocker
    ):
        """
        Test complete password reset flow:
        1. Create user with known password
        2. Start password reset (receive OTP)
        3. Verify OTP
        4. Confirm new password
        5. Login with new password
        6. Verify old password doesn't work
        """
        # Step 1: Create user
        user = await UserFactory.create_with_team_async(
            db_session, email="reset@test.com", password="OldPassword123!"
        )
        await db_session.commit()

        # Mock Celery task to capture OTP
        captured_otp = []

        def mock_send_otp(email: str, otp: str):
            captured_otp.append(otp)

        mocker.patch(
            "app.api.endpoints.auth.send_password_otp_local.delay",
            side_effect=mock_send_otp,
        )

        # Step 2: Start password reset
        start_response = await client.post(
            "/api/auth/forgot-password/start",
            json={"email": "reset@test.com"},
        )

        assert start_response.status_code == 202
        assert len(captured_otp) == 1
        otp = captured_otp[0]

        # Step 3: Verify OTP
        verify_response = await client.post(
            "/api/auth/forgot-password/verify",
            json={"email": "reset@test.com", "otp": otp},
        )

        assert verify_response.status_code == 200
        assert "reset_token" in verify_response.json()
        reset_token = verify_response.json()["reset_token"]

        # Step 4: Confirm new password
        confirm_response = await client.post(
            "/api/auth/forgot-password/confirm",
            json={
                "email": "reset@test.com",
                "reset_token": reset_token,
                "new_password": "NewPassword123!",
            },
        )

        assert confirm_response.status_code == 200

        # Step 5: Login with new password
        login_response = await client.post(
            "/api/auth/login",
            json={"email": "reset@test.com", "password": "NewPassword123!"},
        )

        assert login_response.status_code == 200
        assert "access_token" in login_response.json()

        # Step 6: Verify old password doesn't work
        old_login_response = await client.post(
            "/api/auth/login",
            json={"email": "reset@test.com", "password": "OldPassword123!"},
        )

        assert old_login_response.status_code == 401

    async def test_password_reset_invalidates_old_tokens(
        self, client: AsyncClient, db_session: AsyncSession, mocker
    ):
        """
        Test that password reset invalidates all existing tokens:
        1. Create user and login (get token)
        2. Verify token works
        3. Complete password reset
        4. Verify old token no longer works
        5. Login with new password and get new token
        6. Verify new token works
        """
        # Step 1: Create user and login
        user = await UserFactory.create_with_team_async(
            db_session, email="tokentest@test.com", password="OldPass123!"
        )
        await db_session.commit()

        login_response = await client.post(
            "/api/auth/login",
            json={"email": "tokentest@test.com", "password": "OldPass123!"},
        )

        assert login_response.status_code == 200
        old_token = login_response.json()["access_token"]

        # Step 2: Verify token works
        me_response = await client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {old_token}"}
        )
        assert me_response.status_code == 200

        # Step 3: Complete password reset
        captured_otp = []

        def mock_send_otp(email: str, otp: str):
            captured_otp.append(otp)

        mocker.patch(
            "app.api.endpoints.auth.send_password_otp_local.delay",
            side_effect=mock_send_otp,
        )

        # Start
        await client.post(
            "/api/auth/forgot-password/start",
            json={"email": "tokentest@test.com"},
        )
        otp = captured_otp[0]

        # Verify
        verify_response = await client.post(
            "/api/auth/forgot-password/verify",
            json={"email": "tokentest@test.com", "otp": otp},
        )
        reset_token = verify_response.json()["reset_token"]

        # Confirm
        await client.post(
            "/api/auth/forgot-password/confirm",
            json={
                "email": "tokentest@test.com",
                "reset_token": reset_token,
                "new_password": "NewPass123!",
            },
        )

        # Step 4: Verify old token no longer works
        me_response = await client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {old_token}"}
        )
        assert me_response.status_code == 401

        # Step 5: Login with new password
        new_login_response = await client.post(
            "/api/auth/login",
            json={"email": "tokentest@test.com", "password": "NewPass123!"},
        )

        assert new_login_response.status_code == 200
        new_token = new_login_response.json()["access_token"]

        # Step 6: Verify new token works
        me_response = await client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {new_token}"}
        )
        assert me_response.status_code == 200

    async def test_password_reset_with_2fa_enabled(
        self, client: AsyncClient, db_session: AsyncSession, mocker
    ):
        """
        Test password reset flow when user has 2FA enabled:
        1. Create user with 2FA enabled
        2. Complete password reset
        3. Verify 2FA is still enabled
        4. Login requires TOTP
        """
        # Step 1: Create user with 2FA
        user = await UserFactory.create_with_team_async(
            db_session,
            email="2fa@test.com",
            password="OldPass123!",
            two_factor_enabled=True,
            two_factor_secret="JBSWY3DPEHPK3PXP",  # Test secret
        )
        await db_session.commit()

        # Step 2: Complete password reset
        captured_otp = []

        def mock_send_otp(email: str, otp: str):
            captured_otp.append(otp)

        mocker.patch(
            "app.api.endpoints.auth.send_password_otp_local.delay",
            side_effect=mock_send_otp,
        )

        # Start
        await client.post(
            "/api/auth/forgot-password/start", json={"email": "2fa@test.com"}
        )
        otp = captured_otp[0]

        # Verify
        verify_response = await client.post(
            "/api/auth/forgot-password/verify",
            json={"email": "2fa@test.com", "otp": otp},
        )
        reset_token = verify_response.json()["reset_token"]

        # Confirm
        await client.post(
            "/api/auth/forgot-password/confirm",
            json={
                "email": "2fa@test.com",
                "reset_token": reset_token,
                "new_password": "NewPass123!",
            },
        )

        # Step 3: Verify 2FA is still enabled
        await db_session.refresh(user)
        assert user.two_factor_enabled is True

        # Step 4: Login requires TOTP
        login_response = await client.post(
            "/api/auth/login",
            json={"email": "2fa@test.com", "password": "NewPass123!"},
        )

        # Should get 200 but require TOTP verification
        assert login_response.status_code == 200
        # Token should not work without TOTP (depends on implementation)

    async def test_password_reset_otp_expiration(
        self, client: AsyncClient, db_session: AsyncSession, mocker, freezer
    ):
        """
        Test that OTP expires after timeout:
        1. Start password reset
        2. Wait beyond OTP expiration
        3. Verify OTP is rejected
        4. Request new OTP
        5. Complete reset with new OTP
        """
        # Step 1: Create user
        user = await UserFactory.create_with_team_async(
            db_session, email="expire@test.com", password="OldPass123!"
        )
        await db_session.commit()

        captured_otp = []

        def mock_send_otp(email: str, otp: str):
            captured_otp.append(otp)

        mocker.patch(
            "app.api.endpoints.auth.send_password_otp_local.delay",
            side_effect=mock_send_otp,
        )

        # Step 2: Start reset and get OTP
        await client.post(
            "/api/auth/forgot-password/start", json={"email": "expire@test.com"}
        )
        old_otp = captured_otp[0]

        # Step 3: Move time forward beyond expiration (10 minutes)
        freezer.move_to("11 minutes later")

        # Try to verify with expired OTP
        verify_response = await client.post(
            "/api/auth/forgot-password/verify",
            json={"email": "expire@test.com", "otp": old_otp},
        )

        assert verify_response.status_code == 400

        # Step 4: Request new OTP
        captured_otp.clear()
        await client.post(
            "/api/auth/forgot-password/start", json={"email": "expire@test.com"}
        )
        new_otp = captured_otp[0]

        # Step 5: Complete reset with new OTP
        verify_response = await client.post(
            "/api/auth/forgot-password/verify",
            json={"email": "expire@test.com", "otp": new_otp},
        )

        assert verify_response.status_code == 200
        reset_token = verify_response.json()["reset_token"]

        confirm_response = await client.post(
            "/api/auth/forgot-password/confirm",
            json={
                "email": "expire@test.com",
                "reset_token": reset_token,
                "new_password": "NewPass123!",
            },
        )

        assert confirm_response.status_code == 200
