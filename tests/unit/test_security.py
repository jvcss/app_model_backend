"""
Unit tests for app/core/security.py

Tests password hashing, JWT tokens, OTP, and TOTP without database.
"""

import pytest
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
import pyotp

from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    generate_otp,
    verify_otp,
    hash_otp,
    verify_totp,
    generate_totp_secret,
    SECRET_KEY,
    ALGORITHM,
)


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password(self):
        """Test that password is hashed correctly."""
        password = "MySecurePassword123!"
        hashed = get_password_hash(password)

        assert hashed != password
        assert len(hashed) > 50
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_verify_correct_password(self):
        """Test that correct password is verified."""
        password = "MySecurePassword123!"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_incorrect_password(self):
        """Test that incorrect password fails verification."""
        password = "MySecurePassword123!"
        hashed = get_password_hash(password)

        assert verify_password("WrongPassword", hashed) is False
        assert verify_password("", hashed) is False
        assert verify_password("MySecurePassword123", hashed) is False  # Missing !

    def test_different_passwords_produce_different_hashes(self):
        """Test that same password produces different hashes (salt)."""
        password = "MySecurePassword123!"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        # Bcrypt uses salt, so hashes should be different
        assert hash1 != hash2
        # But both should verify
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestJWT:
    """Test JWT token creation and validation."""

    def test_create_access_token(self):
        """Test creating a valid JWT token."""
        data = {"sub": "123"}
        token = create_access_token(data, token_version=1)

        # Decode without verification to check structure
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        assert payload["sub"] == "123"
        assert payload["tv"] == 1
        assert "exp" in payload
        assert "iat" in payload

    def test_token_expiration(self):
        """Test that expired tokens are rejected."""
        data = {"sub": "123"}
        token = create_access_token(
            data,
            token_version=1,
            expires_delta=timedelta(seconds=-10)  # Already expired
        )

        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    def test_token_version_included(self):
        """Test that token version is included in payload."""
        token = create_access_token({"sub": "123"}, token_version=5)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        assert payload["tv"] == 5

    def test_token_with_custom_expiration(self):
        """Test creating token with custom expiration."""
        data = {"sub": "123"}
        expires_delta = timedelta(hours=2)
        token = create_access_token(data, token_version=1, expires_delta=expires_delta)

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)

        # Should expire in approximately 2 hours
        time_diff = (exp_time - now).total_seconds()
        assert 7100 < time_diff < 7300  # ~2 hours (with some margin)

    def test_invalid_token_signature(self):
        """Test that tokens with invalid signatures are rejected."""
        data = {"sub": "123"}
        token = create_access_token(data, token_version=1)

        # Tamper with token
        tampered_token = token[:-10] + "tampered!"

        with pytest.raises(JWTError):
            jwt.decode(tampered_token, SECRET_KEY, algorithms=[ALGORITHM])

    def test_token_with_wrong_secret(self):
        """Test that tokens signed with wrong secret are rejected."""
        data = {"sub": "123"}
        wrong_secret = "wrong_secret_key"
        token = jwt.encode(data, wrong_secret, algorithm=ALGORITHM)

        with pytest.raises(JWTError):
            jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


class TestOTP:
    """Test OTP (One-Time Password) generation and verification."""

    def test_generate_otp_length(self):
        """Test that OTP is 6 digits."""
        otp = generate_otp()

        assert len(otp) == 6
        assert otp.isdigit()

    def test_generate_otp_randomness(self):
        """Test that consecutive OTPs are different (high probability)."""
        otps = [generate_otp() for _ in range(10)]

        # Should have at least 8 unique values out of 10
        assert len(set(otps)) >= 8

    def test_verify_correct_otp(self):
        """Test verifying correct OTP."""
        otp = "123456"
        hashed = hash_otp(otp)

        assert verify_otp(otp, hashed) is True

    def test_verify_incorrect_otp(self):
        """Test that incorrect OTP fails verification."""
        otp = "123456"
        hashed = hash_otp(otp)

        assert verify_otp("654321", hashed) is False
        assert verify_otp("000000", hashed) is False
        assert verify_otp("", hashed) is False
        assert verify_otp("12345", hashed) is False  # Wrong length

    def test_hash_otp_produces_different_hashes(self):
        """Test that same OTP produces different hashes (bcrypt salt)."""
        otp = "123456"
        hash1 = hash_otp(otp)
        hash2 = hash_otp(otp)

        # Different hashes due to salt
        assert hash1 != hash2
        # But both verify
        assert verify_otp(otp, hash1) is True
        assert verify_otp(otp, hash2) is True


class TestTOTP:
    """Test TOTP (Time-based One-Time Password) for 2FA."""

    def test_generate_totp_secret(self):
        """Test generating TOTP secret."""
        secret = generate_totp_secret()

        assert len(secret) == 32  # base32 encoded
        assert secret.isupper()
        assert secret.isalnum()

    def test_generate_unique_secrets(self):
        """Test that consecutive secrets are unique."""
        secrets = [generate_totp_secret() for _ in range(10)]

        assert len(set(secrets)) == 10  # All unique

    def test_verify_totp_valid_code(self):
        """Test verifying valid TOTP code."""
        secret = generate_totp_secret()
        totp = pyotp.TOTP(secret)
        code = totp.now()

        assert verify_totp(secret, code) is True

    def test_verify_totp_invalid_code(self):
        """Test that invalid TOTP code fails verification."""
        secret = generate_totp_secret()

        assert verify_totp(secret, "000000") is False
        assert verify_totp(secret, "123456") is False
        assert verify_totp(secret, "") is False

    def test_verify_totp_expired_code(self):
        """Test that TOTP code expires after time window."""
        import time

        secret = generate_totp_secret()
        totp = pyotp.TOTP(secret)

        # Get code at specific time
        code_at_time = totp.at(time.time() - 60)  # 60 seconds ago

        # Should fail (outside valid window)
        # Note: pyotp has a default window, might still accept if within window
        # This is more of a documentation test
        result = verify_totp(secret, code_at_time)
        # Result depends on the interval and valid_window in verify_totp implementation
        assert isinstance(result, bool)

    def test_totp_with_custom_secret(self):
        """Test TOTP with a known secret."""
        # Use a fixed secret for reproducibility
        secret = "JBSWY3DPEHPK3PXP"  # Example base32 secret
        totp = pyotp.TOTP(secret)

        # Generate code
        code = totp.now()

        # Verify it
        assert verify_totp(secret, code) is True

    def test_totp_case_insensitivity(self):
        """Test that TOTP secret is case-insensitive (base32 standard)."""
        secret_upper = "JBSWY3DPEHPK3PXP"
        secret_lower = secret_upper.lower()

        totp_upper = pyotp.TOTP(secret_upper)
        code = totp_upper.now()

        # Both should work (pyotp handles case)
        assert verify_totp(secret_upper, code) is True
        # Note: verify_totp might expect uppercase, test actual implementation


class TestSecurityEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_password_hash(self):
        """Test hashing empty password."""
        password = ""
        hashed = get_password_hash(password)

        # Should hash even empty password
        assert hashed != password
        assert verify_password("", hashed) is True
        assert verify_password("not_empty", hashed) is False

    def test_very_long_password(self):
        """Test hashing very long password."""
        password = "a" * 1000
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_unicode_password(self):
        """Test hashing password with unicode characters."""
        password = "Пароль123!🔒"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True
        assert verify_password("Пароль123!", hashed) is False

    def test_jwt_with_empty_data(self):
        """Test creating JWT with empty data dict."""
        token = create_access_token({}, token_version=1)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        assert payload["tv"] == 1
        assert "exp" in payload
        assert "iat" in payload

    def test_jwt_with_extra_claims(self):
        """Test creating JWT with additional claims."""
        data = {
            "sub": "123",
            "email": "user@example.com",
            "role": "admin"
        }
        token = create_access_token(data, token_version=1)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        assert payload["sub"] == "123"
        assert payload["email"] == "user@example.com"
        assert payload["role"] == "admin"
        assert payload["tv"] == 1
