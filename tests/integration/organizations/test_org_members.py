"""
Integration tests for organization members management.

Tests:
- POST /api/organizations/{org_id}/members - Add member
- GET /api/organizations/{org_id}/members - List members
- PATCH /api/organizations/{org_id}/members/{user_id} - Update member
- DELETE /api/organizations/{org_id}/members/{user_id} - Remove member
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization_member import OrganizationMember
from tests.factories import (
    UserFactory,
    OrganizationFactory,
    OrganizationMemberFactory
)


@pytest.mark.asyncio
class TestAddOrganizationMember:
    """Test POST /api/organizations/{org_id}/members - Add member."""

    async def test_add_member_as_admin(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test admin can add members to organization."""
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

        # New user to add
        new_user = await UserFactory.create_async(
            db_session,
            email="newmember@test.com"
        )
        await db_session.commit()

        response = await client.post(
            f"/api/organizations/{org.id}/members",
            headers=auth_headers,
            json={
                "user_id": new_user.id,
                "role": "member"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["organization_id"] == org.id
        assert data["user_id"] == new_user.id
        assert data["role"] == "member"
        assert data["status"] == "active"

        # Verify in DB
        result = await db_session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org.id,
                OrganizationMember.user_id == new_user.id
            )
        )
        om = result.scalar_one_or_none()
        assert om is not None
        assert om.role == "member"

    async def test_add_member_with_admin_role(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test adding member with admin role."""
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

        new_user = await UserFactory.create_async(db_session, email="admin2@test.com")
        await db_session.commit()

        response = await client.post(
            f"/api/organizations/{org.id}/members",
            headers=auth_headers,
            json={
                "user_id": new_user.id,
                "role": "admin"
            }
        )

        assert response.status_code == 201
        assert response.json()["role"] == "admin"

    async def test_add_member_as_non_admin_fails(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test that non-admin members cannot add members."""
        org = await OrganizationFactory.create_async(db_session)
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=user.id,
            role="member"  # Not admin
        )

        new_user = await UserFactory.create_async(db_session, email="new@test.com")
        await db_session.commit()

        response = await client.post(
            f"/api/organizations/{org.id}/members",
            headers=auth_headers,
            json={"user_id": new_user.id, "role": "member"}
        )

        assert response.status_code == 403

    async def test_add_duplicate_member_fails(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test adding same user twice fails."""
        org = await OrganizationFactory.create_async(db_session)
        existing_member = await UserFactory.create_async(
            db_session,
            email="existing@test.com"
        )

        # Add user as admin
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=user.id,
            role="admin"
        )
        # Add existing member
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=existing_member.id,
            role="member"
        )
        await db_session.commit()

        # Try to add existing member again
        response = await client.post(
            f"/api/organizations/{org.id}/members",
            headers=auth_headers,
            json={"user_id": existing_member.id, "role": "admin"}
        )

        assert response.status_code == 400

    async def test_add_member_invalid_user_id(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test adding non-existent user."""
        org = await OrganizationFactory.create_async(db_session)
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=user.id,
            role="admin"
        )
        await db_session.commit()

        response = await client.post(
            f"/api/organizations/{org.id}/members",
            headers=auth_headers,
            json={"user_id": 99999, "role": "member"}
        )

        assert response.status_code == 404

    async def test_add_member_invalid_role(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test adding member with invalid role."""
        org = await OrganizationFactory.create_async(db_session)
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=user.id,
            role="admin"
        )
        new_user = await UserFactory.create_async(db_session, email="new@test.com")
        await db_session.commit()

        response = await client.post(
            f"/api/organizations/{org.id}/members",
            headers=auth_headers,
            json={"user_id": new_user.id, "role": "invalid_role"}
        )

        assert response.status_code == 422

    async def test_add_member_no_auth(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test adding member without authentication."""
        org = await OrganizationFactory.create_async(db_session)
        await db_session.commit()

        response = await client.post(
            f"/api/organizations/{org.id}/members",
            json={"user_id": 1, "role": "member"}
        )

        assert response.status_code == 401


@pytest.mark.asyncio
class TestListOrganizationMembers:
    """Test GET /api/organizations/{org_id}/members - List members."""

    async def test_list_members_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test listing organization members."""
        org = await OrganizationFactory.create_async(db_session)

        # Add current user as admin
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=user.id,
            role="admin"
        )

        # Add other members
        member1 = await UserFactory.create_async(db_session, email="member1@test.com")
        member2 = await UserFactory.create_async(db_session, email="member2@test.com")
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=member1.id,
            role="member"
        )
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=member2.id,
            role="member"
        )
        await db_session.commit()

        response = await client.get(
            f"/api/organizations/{org.id}/members",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3  # Current user + 2 members

        # Check user IDs present
        user_ids = [m["user_id"] for m in data]
        assert user.id in user_ids
        assert member1.id in user_ids
        assert member2.id in user_ids

    async def test_list_members_as_non_member_fails(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test that non-members cannot list members."""
        org = await OrganizationFactory.create_async(db_session)
        # Don't add user as member
        await db_session.commit()

        response = await client.get(
            f"/api/organizations/{org.id}/members",
            headers=auth_headers
        )

        assert response.status_code in [403, 404]

    async def test_list_members_includes_role_info(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test that member list includes role information."""
        org = await OrganizationFactory.create_async(db_session)
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=user.id,
            role="admin"
        )

        member = await UserFactory.create_async(db_session, email="member@test.com")
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=member.id,
            role="member"
        )
        await db_session.commit()

        response = await client.get(
            f"/api/organizations/{org.id}/members",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Find admin and member
        roles = {m["user_id"]: m["role"] for m in data}
        assert roles[user.id] == "admin"
        assert roles[member.id] == "member"

    async def test_list_members_no_auth(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test listing members without authentication."""
        org = await OrganizationFactory.create_async(db_session)
        await db_session.commit()

        response = await client.get(f"/api/organizations/{org.id}/members")

        assert response.status_code == 401


@pytest.mark.asyncio
class TestUpdateOrganizationMember:
    """Test PATCH /api/organizations/{org_id}/members/{user_id} - Update member."""

    async def test_update_member_role_as_admin(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test admin can update member role."""
        org = await OrganizationFactory.create_async(db_session)
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=user.id,
            role="admin"
        )

        member = await UserFactory.create_async(db_session, email="member@test.com")
        om = await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=member.id,
            role="member"
        )
        await db_session.commit()

        response = await client.patch(
            f"/api/organizations/{org.id}/members/{member.id}",
            headers=auth_headers,
            json={"role": "admin"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "admin"

        # Verify in DB
        await db_session.refresh(om)
        assert om.role == "admin"

    async def test_update_member_status(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test updating member status."""
        org = await OrganizationFactory.create_async(db_session)
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=user.id,
            role="admin"
        )

        member = await UserFactory.create_async(db_session, email="member@test.com")
        om = await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=member.id,
            role="member",
            status="active"
        )
        await db_session.commit()

        response = await client.patch(
            f"/api/organizations/{org.id}/members/{member.id}",
            headers=auth_headers,
            json={"status": "inactive"}
        )

        assert response.status_code == 200
        assert response.json()["status"] == "inactive"

    async def test_update_member_as_non_admin_fails(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test that non-admin cannot update members."""
        org = await OrganizationFactory.create_async(db_session)
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=user.id,
            role="member"  # Not admin
        )

        other_member = await UserFactory.create_async(
            db_session,
            email="other@test.com"
        )
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=other_member.id,
            role="member"
        )
        await db_session.commit()

        response = await client.patch(
            f"/api/organizations/{org.id}/members/{other_member.id}",
            headers=auth_headers,
            json={"role": "admin"}
        )

        assert response.status_code == 403

    async def test_update_member_not_found(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test updating non-existent member."""
        org = await OrganizationFactory.create_async(db_session)
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=user.id,
            role="admin"
        )
        await db_session.commit()

        response = await client.patch(
            f"/api/organizations/{org.id}/members/99999",
            headers=auth_headers,
            json={"role": "admin"}
        )

        assert response.status_code == 404


@pytest.mark.asyncio
class TestRemoveOrganizationMember:
    """Test DELETE /api/organizations/{org_id}/members/{user_id} - Remove member."""

    async def test_remove_member_as_admin(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test admin can remove members."""
        org = await OrganizationFactory.create_async(db_session)
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=user.id,
            role="admin"
        )

        member = await UserFactory.create_async(db_session, email="member@test.com")
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=member.id,
            role="member"
        )
        await db_session.commit()

        response = await client.delete(
            f"/api/organizations/{org.id}/members/{member.id}",
            headers=auth_headers
        )

        assert response.status_code == 204

        # Verify removed from DB
        result = await db_session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org.id,
                OrganizationMember.user_id == member.id
            )
        )
        om = result.scalar_one_or_none()
        assert om is None

    async def test_remove_member_as_non_admin_fails(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test that non-admin cannot remove members."""
        org = await OrganizationFactory.create_async(db_session)
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=user.id,
            role="member"
        )

        other_member = await UserFactory.create_async(
            db_session,
            email="other@test.com"
        )
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=other_member.id,
            role="member"
        )
        await db_session.commit()

        response = await client.delete(
            f"/api/organizations/{org.id}/members/{other_member.id}",
            headers=auth_headers
        )

        assert response.status_code == 403

    async def test_cannot_remove_last_admin(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test that last admin cannot be removed."""
        org = await OrganizationFactory.create_async(db_session)
        # Only one admin
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=user.id,
            role="admin"
        )

        # Add regular member
        member = await UserFactory.create_async(db_session, email="member@test.com")
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=member.id,
            role="member"
        )
        await db_session.commit()

        # Try to remove the only admin
        response = await client.delete(
            f"/api/organizations/{org.id}/members/{user.id}",
            headers=auth_headers
        )

        # Should fail - must have at least one admin
        assert response.status_code == 400

    async def test_remove_member_not_found(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test removing non-existent member."""
        org = await OrganizationFactory.create_async(db_session)
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=user.id,
            role="admin"
        )
        await db_session.commit()

        response = await client.delete(
            f"/api/organizations/{org.id}/members/99999",
            headers=auth_headers
        )

        assert response.status_code == 404


@pytest.mark.asyncio
class TestOrganizationMembersEdgeCases:
    """Test edge cases for organization members."""

    async def test_member_can_be_in_multiple_organizations(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test that a user can be member of multiple organizations."""
        # Create 3 organizations
        org1 = await OrganizationFactory.create_async(
            db_session,
            name="Org 1"
        )
        org2 = await OrganizationFactory.create_async(
            db_session,
            name="Org 2"
        )
        org3 = await OrganizationFactory.create_async(
            db_session,
            name="Org 3"
        )

        # Add user as member to all
        for org in [org1, org2, org3]:
            await OrganizationMemberFactory.create_async(
                db_session,
                organization_id=org.id,
                user_id=user.id,
                role="admin"
            )
        await db_session.commit()

        # User should see all 3 organizations
        response = await client.get("/api/organizations/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3

        org_names = [o["name"] for o in data]
        assert "Org 1" in org_names
        assert "Org 2" in org_names
        assert "Org 3" in org_names

    async def test_organization_can_have_multiple_admins(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test that organization can have multiple admins."""
        org = await OrganizationFactory.create_async(db_session)

        # Add current user as admin
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=user.id,
            role="admin"
        )

        # Add 2 more admins
        admin2 = await UserFactory.create_async(db_session, email="admin2@test.com")
        admin3 = await UserFactory.create_async(db_session, email="admin3@test.com")

        for admin_user in [admin2, admin3]:
            await OrganizationMemberFactory.create_async(
                db_session,
                organization_id=org.id,
                user_id=admin_user.id,
                role="admin"
            )
        await db_session.commit()

        # List members
        response = await client.get(
            f"/api/organizations/{org.id}/members",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Count admins
        admin_count = sum(1 for m in data if m["role"] == "admin")
        assert admin_count >= 3

    async def test_creator_automatically_becomes_admin(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test that creator is automatically added as admin."""
        response = await client.post(
            "/api/organizations/",
            headers=auth_headers,
            json={
                "name": "New Org",
                "organization_type": "provider"
            }
        )

        assert response.status_code == 201
        org_id = response.json()["id"]

        # List members
        members_response = await client.get(
            f"/api/organizations/{org_id}/members",
            headers=auth_headers
        )

        assert members_response.status_code == 200
        members = members_response.json()

        # Creator should be in members list as admin
        creator_member = next((m for m in members if m["user_id"] == user.id), None)
        assert creator_member is not None
        assert creator_member["role"] == "admin"
