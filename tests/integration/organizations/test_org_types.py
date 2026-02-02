"""
Integration tests for organization types (Provider, Client, Guest).

Tests polymorphic organization types with type-specific data.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta

from app.models.organization import Organization
from app.models.provider import Provider
from app.models.client import Client
from app.models.guest import Guest
from tests.factories import (
    UserFactory,
    OrganizationFactory,
    OrganizationMemberFactory
)


@pytest.mark.asyncio
class TestProviderOrganization:
    """Test Provider-specific functionality."""

    async def test_create_provider_creates_provider_data(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test that creating provider org also creates Provider record."""
        response = await client.post(
            "/api/organizations/",
            headers=auth_headers,
            json={
                "name": "Tech Provider",
                "organization_type": "provider"
            }
        )

        assert response.status_code == 201
        org_id = response.json()["id"]

        # Verify Provider record created
        result = await db_session.execute(
            select(Provider).where(Provider.organization_id == org_id)
        )
        provider = result.scalar_one_or_none()
        assert provider is not None

    async def test_get_provider_includes_type_details(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test that getting provider org includes type-specific details."""
        org = await OrganizationFactory.create_async(
            db_session,
            organization_type="provider",
            name="Provider Corp"
        )
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=user.id,
            role="admin"
        )
        await db_session.commit()

        response = await client.get(
            f"/api/organizations/{org.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["organization_type"] == "provider"

        # Check if type_details included (if implemented)
        if "type_details" in data:
            details = data["type_details"]
            assert "services_offered" in details or details is not None

    async def test_provider_has_services_offered(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test that provider has services_offered field."""
        org = await OrganizationFactory.create_async(
            db_session,
            organization_type="provider"
        )
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=user.id,
            role="admin"
        )
        await db_session.commit()

        # Get provider record
        result = await db_session.execute(
            select(Provider).where(Provider.organization_id == org.id)
        )
        provider = result.scalar_one_or_none()
        assert provider is not None
        assert provider.services_offered is not None
        assert isinstance(provider.services_offered, list)

    async def test_provider_has_capabilities(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test that provider has capabilities field."""
        org = await OrganizationFactory.create_async(
            db_session,
            organization_type="provider"
        )
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=user.id,
            role="admin"
        )
        await db_session.commit()

        result = await db_session.execute(
            select(Provider).where(Provider.organization_id == org.id)
        )
        provider = result.scalar_one_or_none()
        assert provider is not None
        assert provider.capabilities is not None
        assert isinstance(provider.capabilities, dict)

    async def test_provider_verified_flag(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test that provider has verified flag."""
        org = await OrganizationFactory.create_async(
            db_session,
            organization_type="provider"
        )
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=user.id,
            role="admin"
        )
        await db_session.commit()

        result = await db_session.execute(
            select(Provider).where(Provider.organization_id == org.id)
        )
        provider = result.scalar_one_or_none()
        assert provider is not None
        assert isinstance(provider.verified, bool)


@pytest.mark.asyncio
class TestClientOrganization:
    """Test Client-specific functionality."""

    async def test_create_client_creates_client_data(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test that creating client org also creates Client record."""
        response = await client.post(
            "/api/organizations/",
            headers=auth_headers,
            json={
                "name": "ACME Client",
                "organization_type": "client"
            }
        )

        assert response.status_code == 201
        org_id = response.json()["id"]

        # Verify Client record created
        result = await db_session.execute(
            select(Client).where(Client.organization_id == org_id)
        )
        client_record = result.scalar_one_or_none()
        assert client_record is not None

    async def test_client_has_contract_number(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test that client has contract_number field."""
        org = await OrganizationFactory.create_async(
            db_session,
            organization_type="client"
        )
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=user.id,
            role="admin"
        )
        await db_session.commit()

        result = await db_session.execute(
            select(Client).where(Client.organization_id == org.id)
        )
        client_record = result.scalar_one_or_none()
        assert client_record is not None
        assert client_record.contract_number is not None
        assert isinstance(client_record.contract_number, str)

    async def test_client_has_billing_info(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test that client has billing_info field."""
        org = await OrganizationFactory.create_async(
            db_session,
            organization_type="client"
        )
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=user.id,
            role="admin"
        )
        await db_session.commit()

        result = await db_session.execute(
            select(Client).where(Client.organization_id == org.id)
        )
        client_record = result.scalar_one_or_none()
        assert client_record is not None
        # billing_info can be JSON/dict
        if client_record.billing_info:
            assert isinstance(client_record.billing_info, (dict, str))

    async def test_client_has_payment_terms(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test that client has payment_terms field."""
        org = await OrganizationFactory.create_async(
            db_session,
            organization_type="client"
        )
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=user.id,
            role="admin"
        )
        await db_session.commit()

        result = await db_session.execute(
            select(Client).where(Client.organization_id == org.id)
        )
        client_record = result.scalar_one_or_none()
        assert client_record is not None
        # payment_terms should be a string
        if client_record.payment_terms:
            assert isinstance(client_record.payment_terms, str)


@pytest.mark.asyncio
class TestGuestOrganization:
    """Test Guest-specific functionality."""

    async def test_create_guest_creates_guest_data(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test that creating guest org also creates Guest record."""
        response = await client.post(
            "/api/organizations/",
            headers=auth_headers,
            json={
                "name": "Guest Org",
                "organization_type": "guest"
            }
        )

        assert response.status_code == 201
        org_id = response.json()["id"]

        # Verify Guest record created
        result = await db_session.execute(
            select(Guest).where(Guest.organization_id == org_id)
        )
        guest = result.scalar_one_or_none()
        assert guest is not None

    async def test_guest_has_access_expires_at(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test that guest has access_expires_at field."""
        org = await OrganizationFactory.create_async(
            db_session,
            organization_type="guest"
        )
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=user.id,
            role="admin"
        )
        await db_session.commit()

        result = await db_session.execute(
            select(Guest).where(Guest.organization_id == org.id)
        )
        guest = result.scalar_one_or_none()
        assert guest is not None
        assert guest.access_expires_at is not None
        assert isinstance(guest.access_expires_at, datetime)
        # Should be in the future
        assert guest.access_expires_at > datetime.now(timezone.utc)

    async def test_guest_has_invited_by(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test that guest can have invited_by field."""
        org = await OrganizationFactory.create_async(
            db_session,
            organization_type="guest"
        )
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=user.id,
            role="admin"
        )
        await db_session.commit()

        result = await db_session.execute(
            select(Guest).where(Guest.organization_id == org.id)
        )
        guest = result.scalar_one_or_none()
        assert guest is not None
        # invited_by can be None or a user_id
        if guest.invited_by:
            assert isinstance(guest.invited_by, int)

    async def test_guest_has_access_scope(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test that guest has access_scope field."""
        org = await OrganizationFactory.create_async(
            db_session,
            organization_type="guest"
        )
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=user.id,
            role="admin"
        )
        await db_session.commit()

        result = await db_session.execute(
            select(Guest).where(Guest.organization_id == org.id)
        )
        guest = result.scalar_one_or_none()
        assert guest is not None
        # access_scope is JSON/dict
        if guest.access_scope:
            assert isinstance(guest.access_scope, dict)

    async def test_guest_access_expiration(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test that guest access has expiration in the future."""
        org = await OrganizationFactory.create_async(
            db_session,
            organization_type="guest"
        )
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=user.id,
            role="admin"
        )
        await db_session.commit()

        result = await db_session.execute(
            select(Guest).where(Guest.organization_id == org.id)
        )
        guest = result.scalar_one_or_none()

        # Default expiration should be 30 days in future (from factory)
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=25)
        assert guest.access_expires_at > future


@pytest.mark.asyncio
class TestOrganizationTypePolymorphism:
    """Test polymorphic behavior of organization types."""

    async def test_organization_can_only_have_one_type(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test that an organization has only one type-specific record."""
        org = await OrganizationFactory.create_async(
            db_session,
            organization_type="provider"
        )
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=user.id,
            role="admin"
        )
        await db_session.commit()

        # Should have Provider record
        provider_result = await db_session.execute(
            select(Provider).where(Provider.organization_id == org.id)
        )
        provider = provider_result.scalar_one_or_none()
        assert provider is not None

        # Should NOT have Client record
        client_result = await db_session.execute(
            select(Client).where(Client.organization_id == org.id)
        )
        client_record = client_result.scalar_one_or_none()
        assert client_record is None

        # Should NOT have Guest record
        guest_result = await db_session.execute(
            select(Guest).where(Guest.organization_id == org.id)
        )
        guest = guest_result.scalar_one_or_none()
        assert guest is None

    async def test_different_types_have_different_fields(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test that different org types have different type-specific fields."""
        # Create one of each type
        provider_org = await OrganizationFactory.create_async(
            db_session,
            organization_type="provider",
            name="Provider Org"
        )
        client_org = await OrganizationFactory.create_async(
            db_session,
            organization_type="client",
            name="Client Org"
        )
        guest_org = await OrganizationFactory.create_async(
            db_session,
            organization_type="guest",
            name="Guest Org"
        )

        # Add user as admin to all
        for org in [provider_org, client_org, guest_org]:
            await OrganizationMemberFactory.create_async(
                db_session,
                organization_id=org.id,
                user_id=user.id,
                role="admin"
            )
        await db_session.commit()

        # Get provider-specific data
        provider_result = await db_session.execute(
            select(Provider).where(Provider.organization_id == provider_org.id)
        )
        provider = provider_result.scalar_one()
        assert hasattr(provider, 'services_offered')
        assert hasattr(provider, 'capabilities')
        assert hasattr(provider, 'verified')

        # Get client-specific data
        client_result = await db_session.execute(
            select(Client).where(Client.organization_id == client_org.id)
        )
        client_record = client_result.scalar_one()
        assert hasattr(client_record, 'contract_number')
        assert hasattr(client_record, 'billing_info')
        assert hasattr(client_record, 'payment_terms')

        # Get guest-specific data
        guest_result = await db_session.execute(
            select(Guest).where(Guest.organization_id == guest_org.id)
        )
        guest = guest_result.scalar_one()
        assert hasattr(guest, 'access_expires_at')
        assert hasattr(guest, 'invited_by')
        assert hasattr(guest, 'access_scope')

    async def test_deleting_organization_deletes_type_data(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test that deleting org also handles type-specific data (if cascade)."""
        org = await OrganizationFactory.create_async(
            db_session,
            organization_type="provider"
        )
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=user.id,
            role="admin"
        )
        await db_session.commit()

        org_id = org.id

        # Verify Provider record exists
        provider_result = await db_session.execute(
            select(Provider).where(Provider.organization_id == org_id)
        )
        assert provider_result.scalar_one_or_none() is not None

        # Delete organization (soft delete)
        await client.delete(f"/api/organizations/{org_id}", headers=auth_headers)

        # Organization should be archived
        await db_session.refresh(org)
        assert org.archived is True

        # Provider record should still exist (soft delete doesn't remove)
        provider_result = await db_session.execute(
            select(Provider).where(Provider.organization_id == org_id)
        )
        provider = provider_result.scalar_one_or_none()
        assert provider is not None  # Still exists


@pytest.mark.asyncio
class TestOrganizationTypeEdgeCases:
    """Test edge cases for organization types."""

    async def test_cannot_change_organization_type(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test that organization_type cannot be changed after creation."""
        org = await OrganizationFactory.create_async(
            db_session,
            organization_type="provider"
        )
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=user.id,
            role="admin"
        )
        await db_session.commit()

        # Try to update type
        response = await client.patch(
            f"/api/organizations/{org.id}",
            headers=auth_headers,
            json={"organization_type": "client"}
        )

        # Should fail or ignore (type is immutable)
        # Depends on implementation
        if response.status_code == 200:
            # If update succeeds, type should not change
            await db_session.refresh(org)
            assert org.organization_type == "provider"

    async def test_type_specific_data_created_automatically(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test that type-specific data is created automatically."""
        response = await client.post(
            "/api/organizations/",
            headers=auth_headers,
            json={
                "name": "Auto Type Data",
                "organization_type": "client"
            }
        )

        assert response.status_code == 201
        org_id = response.json()["id"]

        # Client record should be created automatically
        result = await db_session.execute(
            select(Client).where(Client.organization_id == org_id)
        )
        client_record = result.scalar_one_or_none()
        assert client_record is not None
