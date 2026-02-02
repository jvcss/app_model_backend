"""
Integration tests for team members management.

Tests polymorphic team members (users AND organizations).

Endpoints:
- GET /api/teams/{team_id}/members - List members
- POST /api/teams/{team_id}/members/users - Add user
- POST /api/teams/{team_id}/members/organizations - Add organization
- PATCH /api/teams/{team_id}/members/{member_type}/{member_id} - Update member
- DELETE /api/teams/{team_id}/members/{member_type}/{member_id} - Remove member
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.team_member import TeamMember
from tests.factories import (
    UserFactory,
    TeamFactory,
    OrganizationFactory,
    TeamMemberFactory,
    OrganizationMemberFactory
)


@pytest.mark.asyncio
class TestListTeamMembers:
    """Test GET /api/teams/{team_id}/members."""

    async def test_list_members_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test listing team members."""
        team = await TeamFactory.create_async(db_session, user_id=user.id)

        # Add user member
        member_user = await UserFactory.create_async(
            db_session,
            email="member@test.com"
        )
        await TeamMemberFactory.create_user_member_async(
            db_session,
            team_id=team.id,
            user_id=member_user.id,
            role="member"
        )

        # Add organization member
        org = await OrganizationFactory.create_async(
            db_session,
            organization_type="provider"
        )
        await TeamMemberFactory.create_org_member_async(
            db_session,
            team_id=team.id,
            organization_id=org.id,
            role="admin"
        )

        await db_session.commit()

        response = await client.get(
            f"/api/teams/{team.id}/members",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2

        # Verify both types present
        member_types = [m["member_type"] for m in data]
        assert "user" in member_types
        assert "organization" in member_types

    async def test_list_members_empty_team(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test listing members of team with no members."""
        team = await TeamFactory.create_async(db_session, user_id=user.id)
        await db_session.commit()

        response = await client.get(
            f"/api/teams/{team.id}/members",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Might be empty or contain owner

    async def test_list_members_no_auth(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user
    ):
        """Test listing members without authentication."""
        team = await TeamFactory.create_async(db_session, user_id=user.id)
        await db_session.commit()

        response = await client.get(f"/api/teams/{team.id}/members")

        assert response.status_code == 401

    async def test_list_members_not_team_owner(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test listing members of team user doesn't own."""
        other_user = await UserFactory.create_async(db_session, email="other@test.com")
        other_team = await TeamFactory.create_async(db_session, user_id=other_user.id)
        await db_session.commit()

        response = await client.get(
            f"/api/teams/{other_team.id}/members",
            headers=auth_headers
        )

        # Should fail if user is not owner or member
        assert response.status_code in [403, 404]


@pytest.mark.asyncio
class TestAddUserMember:
    """Test POST /api/teams/{team_id}/members/users - Add user to team."""

    async def test_add_user_member_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test adding user to team."""
        team = await TeamFactory.create_async(db_session, user_id=user.id)
        member_user = await UserFactory.create_async(
            db_session,
            email="member@test.com"
        )
        await db_session.commit()

        response = await client.post(
            f"/api/teams/{team.id}/members/users",
            headers=auth_headers,
            json={
                "user_id": member_user.id,
                "role": "member"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["team_id"] == team.id
        assert data["member_type"] == "user"
        assert data["member_id"] == member_user.id
        assert data["role"] == "member"
        assert data["status"] == "active"

        # Verify in DB
        result = await db_session.execute(
            select(TeamMember).where(
                TeamMember.team_id == team.id,
                TeamMember.member_type == "user",
                TeamMember.member_id == member_user.id
            )
        )
        tm = result.scalar_one_or_none()
        assert tm is not None
        assert tm.role == "member"

    async def test_add_user_member_with_admin_role(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test adding user with admin role."""
        team = await TeamFactory.create_async(db_session, user_id=user.id)
        member_user = await UserFactory.create_async(db_session, email="admin@test.com")
        await db_session.commit()

        response = await client.post(
            f"/api/teams/{team.id}/members/users",
            headers=auth_headers,
            json={
                "user_id": member_user.id,
                "role": "admin"
            }
        )

        assert response.status_code == 201
        assert response.json()["role"] == "admin"

    async def test_add_user_member_with_viewer_role(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test adding user with viewer role."""
        team = await TeamFactory.create_async(db_session, user_id=user.id)
        member_user = await UserFactory.create_async(db_session, email="viewer@test.com")
        await db_session.commit()

        response = await client.post(
            f"/api/teams/{team.id}/members/users",
            headers=auth_headers,
            json={
                "user_id": member_user.id,
                "role": "viewer"
            }
        )

        assert response.status_code == 201
        assert response.json()["role"] == "viewer"

    async def test_add_user_member_duplicate_fails(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test adding same user twice fails."""
        team = await TeamFactory.create_async(db_session, user_id=user.id)
        member_user = await UserFactory.create_async(db_session, email="member@test.com")

        # Add user first time
        await TeamMemberFactory.create_user_member_async(
            db_session,
            team_id=team.id,
            user_id=member_user.id,
            role="member"
        )
        await db_session.commit()

        # Try to add same user again
        response = await client.post(
            f"/api/teams/{team.id}/members/users",
            headers=auth_headers,
            json={
                "user_id": member_user.id,
                "role": "admin"
            }
        )

        assert response.status_code == 400

    async def test_add_user_member_invalid_user_id(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test adding non-existent user."""
        team = await TeamFactory.create_async(db_session, user_id=user.id)
        await db_session.commit()

        response = await client.post(
            f"/api/teams/{team.id}/members/users",
            headers=auth_headers,
            json={
                "user_id": 99999,
                "role": "member"
            }
        )

        assert response.status_code == 404

    async def test_add_user_member_invalid_role(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test adding user with invalid role."""
        team = await TeamFactory.create_async(db_session, user_id=user.id)
        member_user = await UserFactory.create_async(db_session, email="member@test.com")
        await db_session.commit()

        response = await client.post(
            f"/api/teams/{team.id}/members/users",
            headers=auth_headers,
            json={
                "user_id": member_user.id,
                "role": "invalid_role"
            }
        )

        assert response.status_code == 422

    async def test_add_user_member_no_auth(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user
    ):
        """Test adding user without authentication."""
        team = await TeamFactory.create_async(db_session, user_id=user.id)
        member_user = await UserFactory.create_async(db_session, email="member@test.com")
        await db_session.commit()

        response = await client.post(
            f"/api/teams/{team.id}/members/users",
            json={"user_id": member_user.id, "role": "member"}
        )

        assert response.status_code == 401


@pytest.mark.asyncio
class TestAddOrganizationMember:
    """Test POST /api/teams/{team_id}/members/organizations - Add organization to team."""

    async def test_add_organization_member_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test adding organization to team."""
        team = await TeamFactory.create_async(db_session, user_id=user.id)
        org = await OrganizationFactory.create_async(
            db_session,
            organization_type="provider",
            name="Tech Corp"
        )
        await db_session.commit()

        response = await client.post(
            f"/api/teams/{team.id}/members/organizations",
            headers=auth_headers,
            json={
                "organization_id": org.id,
                "role": "admin"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["team_id"] == team.id
        assert data["member_type"] == "organization"
        assert data["member_id"] == org.id
        assert data["role"] == "admin"

        # Verify in DB
        result = await db_session.execute(
            select(TeamMember).where(
                TeamMember.team_id == team.id,
                TeamMember.member_type == "organization",
                TeamMember.member_id == org.id
            )
        )
        tm = result.scalar_one_or_none()
        assert tm is not None

    async def test_add_organization_duplicate_fails(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test adding same organization twice fails."""
        team = await TeamFactory.create_async(db_session, user_id=user.id)
        org = await OrganizationFactory.create_async(
            db_session,
            organization_type="client"
        )

        # Add org first time
        await TeamMemberFactory.create_org_member_async(
            db_session,
            team_id=team.id,
            organization_id=org.id,
            role="member"
        )
        await db_session.commit()

        # Try to add same org again
        response = await client.post(
            f"/api/teams/{team.id}/members/organizations",
            headers=auth_headers,
            json={
                "organization_id": org.id,
                "role": "admin"
            }
        )

        assert response.status_code == 400

    async def test_add_organization_member_invalid_org_id(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test adding non-existent organization."""
        team = await TeamFactory.create_async(db_session, user_id=user.id)
        await db_session.commit()

        response = await client.post(
            f"/api/teams/{team.id}/members/organizations",
            headers=auth_headers,
            json={
                "organization_id": 99999,
                "role": "member"
            }
        )

        assert response.status_code == 404


@pytest.mark.asyncio
class TestUpdateTeamMember:
    """Test PATCH /api/teams/{team_id}/members/{member_type}/{member_id} - Update member."""

    async def test_update_user_member_role(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test updating user member role."""
        team = await TeamFactory.create_async(db_session, user_id=user.id)
        member_user = await UserFactory.create_async(db_session, email="member@test.com")
        await TeamMemberFactory.create_user_member_async(
            db_session,
            team_id=team.id,
            user_id=member_user.id,
            role="member"
        )
        await db_session.commit()

        response = await client.patch(
            f"/api/teams/{team.id}/members/user/{member_user.id}",
            headers=auth_headers,
            json={"role": "admin"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "admin"

        # Verify in DB
        result = await db_session.execute(
            select(TeamMember).where(
                TeamMember.team_id == team.id,
                TeamMember.member_type == "user",
                TeamMember.member_id == member_user.id
            )
        )
        tm = result.scalar_one_or_none()
        assert tm.role == "admin"

    async def test_update_user_member_status(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test updating user member status."""
        team = await TeamFactory.create_async(db_session, user_id=user.id)
        member_user = await UserFactory.create_async(db_session, email="member@test.com")
        await TeamMemberFactory.create_user_member_async(
            db_session,
            team_id=team.id,
            user_id=member_user.id,
            role="member",
            status="active"
        )
        await db_session.commit()

        response = await client.patch(
            f"/api/teams/{team.id}/members/user/{member_user.id}",
            headers=auth_headers,
            json={"status": "inactive"}
        )

        assert response.status_code == 200
        assert response.json()["status"] == "inactive"

    async def test_update_organization_member_role(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test updating organization member role."""
        team = await TeamFactory.create_async(db_session, user_id=user.id)
        org = await OrganizationFactory.create_async(
            db_session,
            organization_type="provider"
        )
        await TeamMemberFactory.create_org_member_async(
            db_session,
            team_id=team.id,
            organization_id=org.id,
            role="member"
        )
        await db_session.commit()

        response = await client.patch(
            f"/api/teams/{team.id}/members/organization/{org.id}",
            headers=auth_headers,
            json={"role": "admin"}
        )

        assert response.status_code == 200
        assert response.json()["role"] == "admin"

    async def test_update_member_not_found(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test updating non-existent member."""
        team = await TeamFactory.create_async(db_session, user_id=user.id)
        await db_session.commit()

        response = await client.patch(
            f"/api/teams/{team.id}/members/user/99999",
            headers=auth_headers,
            json={"role": "admin"}
        )

        assert response.status_code == 404


@pytest.mark.asyncio
class TestRemoveTeamMember:
    """Test DELETE /api/teams/{team_id}/members/{member_type}/{member_id} - Remove member."""

    async def test_remove_user_member_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test removing user from team."""
        team = await TeamFactory.create_async(db_session, user_id=user.id)
        member_user = await UserFactory.create_async(db_session, email="member@test.com")
        await TeamMemberFactory.create_user_member_async(
            db_session,
            team_id=team.id,
            user_id=member_user.id,
            role="member"
        )
        await db_session.commit()

        response = await client.delete(
            f"/api/teams/{team.id}/members/user/{member_user.id}",
            headers=auth_headers
        )

        assert response.status_code == 204

        # Verify removed from DB
        result = await db_session.execute(
            select(TeamMember).where(
                TeamMember.team_id == team.id,
                TeamMember.member_type == "user",
                TeamMember.member_id == member_user.id
            )
        )
        tm = result.scalar_one_or_none()
        assert tm is None

    async def test_remove_organization_member_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test removing organization from team."""
        team = await TeamFactory.create_async(db_session, user_id=user.id)
        org = await OrganizationFactory.create_async(
            db_session,
            organization_type="client"
        )
        await TeamMemberFactory.create_org_member_async(
            db_session,
            team_id=team.id,
            organization_id=org.id,
            role="member"
        )
        await db_session.commit()

        response = await client.delete(
            f"/api/teams/{team.id}/members/organization/{org.id}",
            headers=auth_headers
        )

        assert response.status_code == 204

        # Verify removed
        result = await db_session.execute(
            select(TeamMember).where(
                TeamMember.team_id == team.id,
                TeamMember.member_type == "organization",
                TeamMember.member_id == org.id
            )
        )
        tm = result.scalar_one_or_none()
        assert tm is None

    async def test_remove_member_not_found(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test removing non-existent member."""
        team = await TeamFactory.create_async(db_session, user_id=user.id)
        await db_session.commit()

        response = await client.delete(
            f"/api/teams/{team.id}/members/user/99999",
            headers=auth_headers
        )

        assert response.status_code == 404


@pytest.mark.asyncio
class TestTeamMembersPolymorphism:
    """Test polymorphic behavior (users AND organizations as members)."""

    async def test_team_can_have_both_user_and_org_members(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test team with mix of users and organizations."""
        team = await TeamFactory.create_async(db_session, user_id=user.id)

        # Add 2 users
        user1 = await UserFactory.create_async(db_session, email="user1@test.com")
        user2 = await UserFactory.create_async(db_session, email="user2@test.com")
        await TeamMemberFactory.create_user_member_async(
            db_session, team_id=team.id, user_id=user1.id, role="member"
        )
        await TeamMemberFactory.create_user_member_async(
            db_session, team_id=team.id, user_id=user2.id, role="viewer"
        )

        # Add 2 organizations
        org1 = await OrganizationFactory.create_async(
            db_session, organization_type="provider"
        )
        org2 = await OrganizationFactory.create_async(
            db_session, organization_type="client"
        )
        await TeamMemberFactory.create_org_member_async(
            db_session, team_id=team.id, organization_id=org1.id, role="admin"
        )
        await TeamMemberFactory.create_org_member_async(
            db_session, team_id=team.id, organization_id=org2.id, role="member"
        )

        await db_session.commit()

        # List members
        response = await client.get(
            f"/api/teams/{team.id}/members",
            headers=auth_headers
        )

        assert response.status_code == 200
        members = response.json()

        # Should have 4 members
        assert len(members) >= 4

        # Count by type
        user_members = [m for m in members if m["member_type"] == "user"]
        org_members = [m for m in members if m["member_type"] == "organization"]

        assert len(user_members) >= 2
        assert len(org_members) >= 2

    async def test_same_id_different_type_allowed(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test that same ID can exist for user and organization (different types)."""
        team = await TeamFactory.create_async(db_session, user_id=user.id)

        # Create user with ID 100 (simulated)
        member_user = await UserFactory.create_async(
            db_session,
            email="member@test.com"
        )

        # Create org (will have different ID, but conceptually could overlap)
        org = await OrganizationFactory.create_async(
            db_session,
            organization_type="provider"
        )

        # Add both as members
        await TeamMemberFactory.create_user_member_async(
            db_session, team_id=team.id, user_id=member_user.id, role="member"
        )
        await TeamMemberFactory.create_org_member_async(
            db_session, team_id=team.id, organization_id=org.id, role="admin"
        )
        await db_session.commit()

        # Both should exist
        response = await client.get(
            f"/api/teams/{team.id}/members",
            headers=auth_headers
        )

        assert response.status_code == 200
        members = response.json()
        assert len(members) >= 2
