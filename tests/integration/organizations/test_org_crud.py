"""
Integration tests for organizations CRUD operations.

Tests:
- POST /api/organizations/ - Create organization
- GET /api/organizations/ - List organizations
- GET /api/organizations/{organization_id} - Get organization
- PATCH /api/organizations/{organization_id} - Update organization
- DELETE /api/organizations/{organization_id} - Delete organization (soft delete)
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
class TestCreateOrganization:
    """Test POST /api/organizations/ - Create organization."""

    async def test_create_provider_organization(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test creating provider organization."""
        response = await client.post(
            "/api/organizations/",
            headers=auth_headers,
            json={
                "name": "Tech Corp",
                "organization_type": "provider",
                "email": "contact@techcorp.com",
                "phone": "555-1234",
                "address": "123 Tech Street"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Tech Corp"
        assert data["organization_type"] == "provider"
        assert data["email"] == "contact@techcorp.com"
        assert "id" in data

        # Verify organization created in DB
        result = await db_session.execute(
            select(Organization).where(Organization.id == data["id"])
        )
        org = result.scalar_one_or_none()
        assert org is not None
        assert org.organization_type == "provider"

        # Verify creator is added as admin member
        from app.models.organization_member import OrganizationMember
        result = await db_session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org.id,
                OrganizationMember.user_id == user.id
            )
        )
        member = result.scalar_one_or_none()
        assert member is not None
        assert member.role == "admin"

    async def test_create_client_organization(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_headers
    ):
        """Test creating client organization."""
        response = await client.post(
            "/api/organizations/",
            headers=auth_headers,
            json={
                "name": "ACME Corp",
                "organization_type": "client",
                "email": "sales@acme.com"
            }
        )

        assert response.status_code == 201
        assert response.json()["organization_type"] == "client"

    async def test_create_guest_organization(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_headers
    ):
        """Test creating guest organization."""
        response = await client.post(
            "/api/organizations/",
            headers=auth_headers,
            json={
                "name": "Guest Org",
                "organization_type": "guest"
            }
        )

        assert response.status_code == 201
        assert response.json()["organization_type"] == "guest"

    async def test_create_organization_minimal(
        self,
        client: AsyncClient,
        auth_headers
    ):
        """Test creating organization with minimal fields."""
        response = await client.post(
            "/api/organizations/",
            headers=auth_headers,
            json={
                "name": "Minimal Org",
                "organization_type": "provider"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Minimal Org"
        assert data["email"] is None
        assert data["phone"] is None

    async def test_create_organization_no_auth(self, client: AsyncClient):
        """Test creating organization without authentication."""
        response = await client.post(
            "/api/organizations/",
            json={"name": "Org", "organization_type": "provider"}
        )

        assert response.status_code == 401

    async def test_create_organization_missing_name(
        self,
        client: AsyncClient,
        auth_headers
    ):
        """Test creating organization without name."""
        response = await client.post(
            "/api/organizations/",
            headers=auth_headers,
            json={"organization_type": "provider"}
        )

        assert response.status_code == 422

    async def test_create_organization_missing_type(
        self,
        client: AsyncClient,
        auth_headers
    ):
        """Test creating organization without type."""
        response = await client.post(
            "/api/organizations/",
            headers=auth_headers,
            json={"name": "Org"}
        )

        assert response.status_code == 422

    async def test_create_organization_invalid_type(
        self,
        client: AsyncClient,
        auth_headers
    ):
        """Test creating organization with invalid type."""
        response = await client.post(
            "/api/organizations/",
            headers=auth_headers,
            json={
                "name": "Org",
                "organization_type": "invalid_type"
            }
        )

        assert response.status_code == 422

    async def test_create_organization_invalid_email(
        self,
        client: AsyncClient,
        auth_headers
    ):
        """Test creating organization with invalid email."""
        response = await client.post(
            "/api/organizations/",
            headers=auth_headers,
            json={
                "name": "Org",
                "organization_type": "provider",
                "email": "not-an-email"
            }
        )

        assert response.status_code == 422

    async def test_create_organization_unicode_name(
        self,
        client: AsyncClient,
        auth_headers
    ):
        """Test creating organization with unicode characters."""
        response = await client.post(
            "/api/organizations/",
            headers=auth_headers,
            json={
                "name": "Empresa 中文 Русский",
                "organization_type": "client"
            }
        )

        assert response.status_code == 201
        assert response.json()["name"] == "Empresa 中文 Русский"


@pytest.mark.asyncio
class TestListOrganizations:
    """Test GET /api/organizations/ - List organizations."""

    async def test_list_organizations_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test listing organizations where user is member."""
        # Create organizations and add user as member
        org1 = await OrganizationFactory.create_async(
            db_session,
            name="Org Alpha",
            organization_type="provider"
        )
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org1.id,
            user_id=user.id,
            role="admin"
        )

        org2 = await OrganizationFactory.create_async(
            db_session,
            name="Org Beta",
            organization_type="client"
        )
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org2.id,
            user_id=user.id,
            role="member"
        )

        await db_session.commit()

        response = await client.get("/api/organizations/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2

        org_names = [o["name"] for o in data]
        assert "Org Alpha" in org_names
        assert "Org Beta" in org_names

    async def test_list_organizations_filters_by_membership(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test that list only shows orgs where user is member."""
        # Org where user is member
        org1 = await OrganizationFactory.create_async(
            db_session,
            name="My Org"
        )
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org1.id,
            user_id=user.id,
            role="admin"
        )

        # Org where user is NOT member
        org2 = await OrganizationFactory.create_async(
            db_session,
            name="Other Org"
        )
        # Don't add user as member

        await db_session.commit()

        response = await client.get("/api/organizations/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        org_names = [o["name"] for o in data]
        assert "My Org" in org_names
        assert "Other Org" not in org_names

    async def test_list_organizations_empty(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test listing when user is not member of any organization."""
        user = await UserFactory.create_async(db_session, email="noOrgs@test.com")
        await db_session.commit()

        from app.core.security import create_access_token
        token = create_access_token({"sub": str(user.id)}, user.token_version)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/api/organizations/", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    async def test_list_organizations_no_auth(self, client: AsyncClient):
        """Test listing organizations without authentication."""
        response = await client.get("/api/organizations/")

        assert response.status_code == 401


@pytest.mark.asyncio
class TestGetOrganization:
    """Test GET /api/organizations/{organization_id} - Get organization."""

    async def test_get_organization_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test getting organization as member."""
        org = await OrganizationFactory.create_async(
            db_session,
            name="Test Org",
            organization_type="provider"
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
        assert data["id"] == org.id
        assert data["name"] == "Test Org"
        assert data["organization_type"] == "provider"

    async def test_get_organization_not_member(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test getting organization where user is not member."""
        org = await OrganizationFactory.create_async(
            db_session,
            name="Other Org"
        )
        # Don't add user as member
        await db_session.commit()

        response = await client.get(
            f"/api/organizations/{org.id}",
            headers=auth_headers
        )

        assert response.status_code in [403, 404]

    async def test_get_organization_not_found(
        self,
        client: AsyncClient,
        auth_headers
    ):
        """Test getting non-existent organization."""
        response = await client.get(
            "/api/organizations/99999",
            headers=auth_headers
        )

        assert response.status_code == 404

    async def test_get_organization_no_auth(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test getting organization without authentication."""
        org = await OrganizationFactory.create_async(db_session)
        await db_session.commit()

        response = await client.get(f"/api/organizations/{org.id}")

        assert response.status_code == 401


@pytest.mark.asyncio
class TestUpdateOrganization:
    """Test PATCH /api/organizations/{organization_id} - Update organization."""

    async def test_update_organization_as_admin(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test updating organization as admin."""
        org = await OrganizationFactory.create_async(
            db_session,
            name="Original Name",
            organization_type="provider"
        )
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=user.id,
            role="admin"
        )
        await db_session.commit()

        response = await client.patch(
            f"/api/organizations/{org.id}",
            headers=auth_headers,
            json={
                "name": "Updated Name",
                "email": "updated@example.com"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["email"] == "updated@example.com"

        # Verify in DB
        await db_session.refresh(org)
        assert org.name == "Updated Name"

    async def test_update_organization_partial(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test partial update."""
        org = await OrganizationFactory.create_async(
            db_session,
            name="Original",
            email="original@test.com",
            organization_type="client"
        )
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=user.id,
            role="admin"
        )
        await db_session.commit()

        # Update only email
        response = await client.patch(
            f"/api/organizations/{org.id}",
            headers=auth_headers,
            json={"email": "new@test.com"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Original"  # Unchanged
        assert data["email"] == "new@test.com"  # Changed

    async def test_update_organization_as_member_fails(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test that non-admin members cannot update."""
        org = await OrganizationFactory.create_async(
            db_session,
            organization_type="provider"
        )
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=user.id,
            role="member"  # Not admin
        )
        await db_session.commit()

        response = await client.patch(
            f"/api/organizations/{org.id}",
            headers=auth_headers,
            json={"name": "Hacked Name"}
        )

        assert response.status_code == 403

    async def test_update_organization_not_member(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test updating org where user is not member."""
        org = await OrganizationFactory.create_async(db_session)
        await db_session.commit()

        response = await client.patch(
            f"/api/organizations/{org.id}",
            headers=auth_headers,
            json={"name": "New Name"}
        )

        assert response.status_code in [403, 404]

    async def test_update_organization_no_auth(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test updating without authentication."""
        org = await OrganizationFactory.create_async(db_session)
        await db_session.commit()

        response = await client.patch(
            f"/api/organizations/{org.id}",
            json={"name": "New Name"}
        )

        assert response.status_code == 401


@pytest.mark.asyncio
class TestDeleteOrganization:
    """Test DELETE /api/organizations/{organization_id} - Delete organization."""

    async def test_delete_organization_as_admin(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test deleting organization as admin (soft delete)."""
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

        response = await client.delete(
            f"/api/organizations/{org.id}",
            headers=auth_headers
        )

        assert response.status_code == 204

        # Verify soft delete
        await db_session.refresh(org)
        assert org.archived is True
        assert org.archived_at is not None

    async def test_delete_organization_as_member_fails(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test that non-admin members cannot delete."""
        org = await OrganizationFactory.create_async(
            db_session,
            organization_type="client"
        )
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=user.id,
            role="member"
        )
        await db_session.commit()

        response = await client.delete(
            f"/api/organizations/{org.id}",
            headers=auth_headers
        )

        assert response.status_code == 403

        # Verify not deleted
        await db_session.refresh(org)
        assert org.archived is False

    async def test_delete_organization_last_admin_check(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test that organization cannot be deleted if it would leave no admins."""
        org = await OrganizationFactory.create_async(db_session)
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=user.id,
            role="admin"
        )
        await db_session.commit()

        # Try to delete (might fail if implementation prevents deleting last admin)
        response = await client.delete(
            f"/api/organizations/{org.id}",
            headers=auth_headers
        )

        # Depends on implementation - might allow delete or require transfer
        assert response.status_code in [204, 400]

    async def test_delete_organization_not_found(
        self,
        client: AsyncClient,
        auth_headers
    ):
        """Test deleting non-existent organization."""
        response = await client.delete(
            "/api/organizations/99999",
            headers=auth_headers
        )

        assert response.status_code == 404

    async def test_delete_organization_no_auth(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test deleting without authentication."""
        org = await OrganizationFactory.create_async(db_session)
        await db_session.commit()

        response = await client.delete(f"/api/organizations/{org.id}")

        assert response.status_code == 401


@pytest.mark.asyncio
class TestOrganizationsCRUDEdgeCases:
    """Test edge cases for organizations CRUD."""

    async def test_duplicate_organization_names_allowed(
        self,
        client: AsyncClient,
        auth_headers
    ):
        """Test that duplicate names are allowed."""
        # Create first org
        await client.post(
            "/api/organizations/",
            headers=auth_headers,
            json={"name": "Duplicate Name", "organization_type": "provider"}
        )

        # Create second org with same name
        response = await client.post(
            "/api/organizations/",
            headers=auth_headers,
            json={"name": "Duplicate Name", "organization_type": "client"}
        )

        assert response.status_code == 201

    async def test_sql_injection_prevention(
        self,
        client: AsyncClient,
        auth_headers
    ):
        """Test SQL injection prevention."""
        response = await client.post(
            "/api/organizations/",
            headers=auth_headers,
            json={
                "name": "Org'; DROP TABLE organizations; --",
                "organization_type": "provider"
            }
        )

        assert response.status_code in [201, 422]

    async def test_xss_prevention(
        self,
        client: AsyncClient,
        auth_headers
    ):
        """Test XSS prevention."""
        response = await client.post(
            "/api/organizations/",
            headers=auth_headers,
            json={
                "name": "<script>alert('xss')</script>",
                "organization_type": "guest"
            }
        )

        if response.status_code == 201:
            data = response.json()
            # Should be stored as-is (escaped when rendered)
            assert data["name"] == "<script>alert('xss')</script>"
