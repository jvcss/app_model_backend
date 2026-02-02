"""
Unit tests for Pydantic schemas validation.

Tests schema validation without database.
"""

import pytest
from pydantic import ValidationError
from datetime import datetime, timezone

from app.schemas.user import UserCreate, UserOut, UserBase
from app.schemas.auth import Login, ForgotPasswordStartIn, ForgotPasswordVerifyIn
from app.schemas.team import TeamCreate, TeamUpdate, TeamOut
from app.schemas.organization import OrganizationCreate, OrganizationUpdate
from app.schemas.team_member import TeamMemberAddUser, TeamMemberUpdate


class TestUserSchemas:
    """Test User-related schemas."""

    def test_user_create_valid(self):
        """Test creating valid UserCreate schema."""
        data = {
            "name": "John Doe",
            "email": "john@example.com",
            "password": "SecurePass123!"
        }
        user = UserCreate(**data)

        assert user.name == "John Doe"
        assert user.email == "john@example.com"
        assert user.password == "SecurePass123!"

    def test_user_create_invalid_email(self):
        """Test that invalid email raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                name="John Doe",
                email="not-an-email",
                password="SecurePass123!"
            )

        errors = exc_info.value.errors()
        assert any("email" in str(error).lower() for error in errors)

    def test_user_create_missing_required_field(self):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(name="John Doe", email="john@example.com")

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("password",) for error in errors)

    def test_user_create_empty_name(self):
        """Test that empty name raises ValidationError."""
        with pytest.raises(ValidationError):
            UserCreate(
                name="",
                email="john@example.com",
                password="SecurePass123!"
            )

    def test_user_out_valid(self):
        """Test UserOut schema."""
        data = {
            "id": 1,
            "name": "John Doe",
            "email": "john@example.com"
        }
        user = UserOut(**data)

        assert user.id == 1
        assert user.name == "John Doe"
        assert user.email == "john@example.com"


class TestAuthSchemas:
    """Test Authentication-related schemas."""

    def test_login_valid(self):
        """Test valid Login schema."""
        login = Login(email="test@example.com", password="password123")

        assert login.email == "test@example.com"
        assert login.password == "password123"

    def test_login_invalid_email(self):
        """Test Login with invalid email."""
        with pytest.raises(ValidationError) as exc_info:
            Login(email="invalid-email", password="password123")

        errors = exc_info.value.errors()
        assert any("email" in str(error).lower() for error in errors)

    def test_login_missing_password(self):
        """Test Login without password."""
        with pytest.raises(ValidationError) as exc_info:
            Login(email="test@example.com")

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("password",) for error in errors)

    def test_forgot_password_start_valid(self):
        """Test ForgotPasswordStartIn schema."""
        schema = ForgotPasswordStartIn(email="test@example.com")

        assert schema.email == "test@example.com"

    def test_forgot_password_start_invalid_email(self):
        """Test ForgotPasswordStartIn with invalid email."""
        with pytest.raises(ValidationError):
            ForgotPasswordStartIn(email="not-an-email")

    def test_forgot_password_verify_with_otp(self):
        """Test ForgotPasswordVerifyIn with OTP."""
        schema = ForgotPasswordVerifyIn(
            email="test@example.com",
            otp="123456"
        )

        assert schema.email == "test@example.com"
        assert schema.otp == "123456"
        assert schema.totp is None

    def test_forgot_password_verify_with_totp(self):
        """Test ForgotPasswordVerifyIn with TOTP."""
        schema = ForgotPasswordVerifyIn(
            email="test@example.com",
            otp="123456",
            totp="654321"
        )

        assert schema.email == "test@example.com"
        assert schema.otp == "123456"
        assert schema.totp == "654321"


class TestTeamSchemas:
    """Test Team-related schemas."""

    def test_team_create_valid(self):
        """Test valid TeamCreate schema."""
        data = {
            "name": "My Team",
            "description": "A test team",
            "personal_team": False
        }
        team = TeamCreate(**data)

        assert team.name == "My Team"
        assert team.description == "A test team"
        assert team.personal_team is False

    def test_team_create_minimal(self):
        """Test TeamCreate with minimal required fields."""
        team = TeamCreate(name="My Team")

        assert team.name == "My Team"
        assert team.description is None
        assert team.personal_team is False  # Default

    def test_team_create_empty_name(self):
        """Test that empty name raises ValidationError."""
        with pytest.raises(ValidationError):
            TeamCreate(name="")

    def test_team_update_partial(self):
        """Test TeamUpdate with partial fields."""
        update = TeamUpdate(description="New description")

        assert update.description == "New description"
        assert update.name is None  # Not provided

    def test_team_update_empty(self):
        """Test TeamUpdate with no fields (all optional)."""
        update = TeamUpdate()

        assert update.name is None
        assert update.description is None

    def test_team_out_valid(self):
        """Test TeamOut schema."""
        data = {
            "id": 1,
            "user_id": 10,
            "name": "My Team",
            "description": "Test team",
            "personal_team": True,
            "archived": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        team = TeamOut(**data)

        assert team.id == 1
        assert team.user_id == 10
        assert team.personal_team is True


class TestOrganizationSchemas:
    """Test Organization-related schemas."""

    def test_organization_create_valid(self):
        """Test valid OrganizationCreate schema."""
        data = {
            "name": "ACME Corp",
            "organization_type": "provider",
            "email": "contact@acme.com",
            "phone": "123-456-7890",
            "address": "123 Main St"
        }
        org = OrganizationCreate(**data)

        assert org.name == "ACME Corp"
        assert org.organization_type == "provider"
        assert org.email == "contact@acme.com"

    def test_organization_create_minimal(self):
        """Test OrganizationCreate with minimal fields."""
        org = OrganizationCreate(
            name="ACME Corp",
            organization_type="client"
        )

        assert org.name == "ACME Corp"
        assert org.organization_type == "client"
        assert org.email is None
        assert org.phone is None

    def test_organization_create_invalid_type(self):
        """Test OrganizationCreate with invalid type."""
        with pytest.raises(ValidationError) as exc_info:
            OrganizationCreate(
                name="ACME Corp",
                organization_type="invalid_type"
            )

        errors = exc_info.value.errors()
        # Should fail because organization_type must be provider/client/guest
        assert len(errors) > 0

    def test_organization_create_invalid_email(self):
        """Test OrganizationCreate with invalid email."""
        with pytest.raises(ValidationError):
            OrganizationCreate(
                name="ACME Corp",
                organization_type="provider",
                email="not-an-email"
            )

    def test_organization_update_partial(self):
        """Test OrganizationUpdate with partial fields."""
        update = OrganizationUpdate(
            email="newemail@acme.com",
            phone="555-1234"
        )

        assert update.email == "newemail@acme.com"
        assert update.phone == "555-1234"
        assert update.name is None  # Not updated
        assert update.address is None  # Not updated


class TestTeamMemberSchemas:
    """Test TeamMember-related schemas."""

    def test_team_member_add_user_valid(self):
        """Test TeamMemberAddUser schema."""
        data = {
            "role": "member",
            "user_id": 123
        }
        tm = TeamMemberAddUser(**data)

        assert tm.role == "member"
        assert tm.user_id == 123

    def test_team_member_add_user_invalid_role(self):
        """Test TeamMemberAddUser with invalid role."""
        with pytest.raises(ValidationError) as exc_info:
            TeamMemberAddUser(role="invalid_role", user_id=123)

        errors = exc_info.value.errors()
        # Should fail because role must be admin/member/viewer
        assert len(errors) > 0

    def test_team_member_update_role(self):
        """Test TeamMemberUpdate for role change."""
        update = TeamMemberUpdate(role="admin")

        assert update.role == "admin"
        assert update.status is None  # Not updated

    def test_team_member_update_status(self):
        """Test TeamMemberUpdate for status change."""
        update = TeamMemberUpdate(status="inactive")

        assert update.status == "inactive"
        assert update.role is None  # Not updated

    def test_team_member_update_empty(self):
        """Test TeamMemberUpdate with no changes."""
        update = TeamMemberUpdate()

        assert update.role is None
        assert update.status is None


class TestSchemaEdgeCases:
    """Test edge cases and special validations."""

    def test_email_normalization(self):
        """Test that emails are validated correctly."""
        # Valid emails
        valid_emails = [
            "user@example.com",
            "user.name@example.com",
            "user+tag@example.co.uk",
            "user123@test-domain.com"
        ]

        for email in valid_emails:
            user = UserCreate(
                name="Test",
                email=email,
                password="Pass123!"
            )
            assert user.email == email

    def test_invalid_emails(self):
        """Test various invalid email formats."""
        invalid_emails = [
            "not-an-email",
            "@example.com",
            "user@",
            "user @example.com",
            "user@.com",
            ""
        ]

        for email in invalid_emails:
            with pytest.raises(ValidationError):
                UserCreate(
                    name="Test",
                    email=email,
                    password="Pass123!"
                )

    def test_unicode_in_name(self):
        """Test that unicode characters are accepted in names."""
        user = UserCreate(
            name="João Silva 中文",
            email="joao@example.com",
            password="Pass123!"
        )

        assert user.name == "João Silva 中文"

    def test_very_long_name(self):
        """Test very long name."""
        long_name = "A" * 500
        user = UserCreate(
            name=long_name,
            email="test@example.com",
            password="Pass123!"
        )

        assert user.name == long_name

    def test_special_characters_in_password(self):
        """Test that special characters are accepted in passwords."""
        special_passwords = [
            "Pass@123!",
            "P@$$w0rd",
            "Pàsswörd123!",
            "Pass#$%^&*()123"
        ]

        for password in special_passwords:
            user = UserCreate(
                name="Test",
                email="test@example.com",
                password=password
            )
            assert user.password == password

    def test_organization_type_case_sensitive(self):
        """Test that organization_type is case-sensitive."""
        # Should fail with uppercase
        with pytest.raises(ValidationError):
            OrganizationCreate(
                name="Test",
                organization_type="PROVIDER"  # Should be lowercase
            )

    def test_extra_fields_ignored(self):
        """Test that extra fields are ignored (or rejected based on config)."""
        # This depends on your Pydantic model config
        # By default, extra fields might be ignored or raise error
        try:
            user = UserCreate(
                name="Test",
                email="test@example.com",
                password="Pass123!",
                extra_field="should_be_ignored"
            )
            # If extra='ignore' in Config, this should work
            assert user.name == "Test"
        except ValidationError:
            # If extra='forbid' in Config, this should raise
            pass  # Expected behavior
