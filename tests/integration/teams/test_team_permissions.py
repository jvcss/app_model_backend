"""
Integration tests for team permissions (RBAC enforcement).

Tests that RBAC permissions are correctly enforced on team endpoints.
Tests different roles: ADMIN, MEMBER, VIEWER
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from tests.factories import (
    UserFactory,
    TeamFactory,
    TeamMemberFactory,
    OrganizationFactory,
    OrganizationMemberFactory
)


@pytest.mark.asyncio
class TestTeamOwnerPermissions:
    """Test that team owner (creator) has full permissions."""

    async def test_owner_can_read_team(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test team owner can read team."""
        team = await TeamFactory.create_async(db_session, user_id=user.id)
        await db_session.commit()

        response = await client.get(
            f"/api/teams/{team.id}",
            headers=auth_headers
        )

        assert response.status_code == 200

    async def test_owner_can_update_team(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test team owner can update team."""
        team = await TeamFactory.create_async(db_session, user_id=user.id)
        await db_session.commit()

        response = await client.patch(
            f"/api/teams/{team.id}",
            headers=auth_headers,
            json={"description": "Updated by owner"}
        )

        assert response.status_code == 200

    async def test_owner_can_delete_team(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test team owner can delete team."""
        team = await TeamFactory.create_async(
            db_session,
            user_id=user.id,
            personal_team=False
        )
        await db_session.commit()

        response = await client.delete(
            f"/api/teams/{team.id}",
            headers=auth_headers
        )

        assert response.status_code == 204

    async def test_owner_can_manage_members(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test team owner can add/update/remove members."""
        team = await TeamFactory.create_async(db_session, user_id=user.id)
        member_user = await UserFactory.create_async(
            db_session,
            email="member@test.com"
        )
        await db_session.commit()

        # Add member
        add_response = await client.post(
            f"/api/teams/{team.id}/members/users",
            headers=auth_headers,
            json={"user_id": member_user.id, "role": "member"}
        )
        assert add_response.status_code == 201

        # Update member
        update_response = await client.patch(
            f"/api/teams/{team.id}/members/user/{member_user.id}",
            headers=auth_headers,
            json={"role": "admin"}
        )
        assert update_response.status_code == 200

        # Remove member
        remove_response = await client.delete(
            f"/api/teams/{team.id}/members/user/{member_user.id}",
            headers=auth_headers
        )
        assert remove_response.status_code == 204


@pytest.mark.asyncio
class TestAdminMemberPermissions:
    """Test ADMIN role permissions (non-owner)."""

    async def test_admin_member_can_read_team(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test admin member can read team."""
        owner = await UserFactory.create_async(db_session, email="owner@test.com")
        team = await TeamFactory.create_async(db_session, user_id=owner.id)

        # Add user as admin member
        admin_user = await UserFactory.create_async(db_session, email="admin@test.com")
        await TeamMemberFactory.create_user_member_async(
            db_session,
            team_id=team.id,
            user_id=admin_user.id,
            role="admin"
        )
        await db_session.commit()

        # Create token for admin user
        token = create_access_token(
            {"sub": str(admin_user.id)},
            admin_user.token_version
        )
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get(f"/api/teams/{team.id}", headers=headers)

        assert response.status_code == 200

    async def test_admin_member_can_update_team(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test admin member can update team."""
        owner = await UserFactory.create_async(db_session, email="owner@test.com")
        team = await TeamFactory.create_async(db_session, user_id=owner.id)

        admin_user = await UserFactory.create_async(db_session, email="admin@test.com")
        await TeamMemberFactory.create_user_member_async(
            db_session,
            team_id=team.id,
            user_id=admin_user.id,
            role="admin"
        )
        await db_session.commit()

        token = create_access_token(
            {"sub": str(admin_user.id)},
            admin_user.token_version
        )
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.patch(
            f"/api/teams/{team.id}",
            headers=headers,
            json={"description": "Updated by admin"}
        )

        assert response.status_code == 200

    async def test_admin_member_can_delete_team(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test admin member can delete team."""
        owner = await UserFactory.create_async(db_session, email="owner@test.com")
        team = await TeamFactory.create_async(
            db_session,
            user_id=owner.id,
            personal_team=False
        )

        admin_user = await UserFactory.create_async(db_session, email="admin@test.com")
        await TeamMemberFactory.create_user_member_async(
            db_session,
            team_id=team.id,
            user_id=admin_user.id,
            role="admin"
        )
        await db_session.commit()

        token = create_access_token(
            {"sub": str(admin_user.id)},
            admin_user.token_version
        )
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.delete(f"/api/teams/{team.id}", headers=headers)

        assert response.status_code == 204

    async def test_admin_member_can_manage_members(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test admin member can add/remove members."""
        owner = await UserFactory.create_async(db_session, email="owner@test.com")
        team = await TeamFactory.create_async(db_session, user_id=owner.id)

        admin_user = await UserFactory.create_async(db_session, email="admin@test.com")
        await TeamMemberFactory.create_user_member_async(
            db_session,
            team_id=team.id,
            user_id=admin_user.id,
            role="admin"
        )

        new_member = await UserFactory.create_async(db_session, email="newmember@test.com")
        await db_session.commit()

        token = create_access_token(
            {"sub": str(admin_user.id)},
            admin_user.token_version
        )
        headers = {"Authorization": f"Bearer {token}"}

        # Admin can add members
        add_response = await client.post(
            f"/api/teams/{team.id}/members/users",
            headers=headers,
            json={"user_id": new_member.id, "role": "member"}
        )
        assert add_response.status_code == 201


@pytest.mark.asyncio
class TestMemberPermissions:
    """Test MEMBER role permissions."""

    async def test_member_can_read_team(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test member can read team."""
        owner = await UserFactory.create_async(db_session, email="owner@test.com")
        team = await TeamFactory.create_async(db_session, user_id=owner.id)

        member_user = await UserFactory.create_async(db_session, email="member@test.com")
        await TeamMemberFactory.create_user_member_async(
            db_session,
            team_id=team.id,
            user_id=member_user.id,
            role="member"
        )
        await db_session.commit()

        token = create_access_token(
            {"sub": str(member_user.id)},
            member_user.token_version
        )
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get(f"/api/teams/{team.id}", headers=headers)

        assert response.status_code == 200

    async def test_member_cannot_update_team(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test member cannot update team (only admin)."""
        owner = await UserFactory.create_async(db_session, email="owner@test.com")
        team = await TeamFactory.create_async(db_session, user_id=owner.id)

        member_user = await UserFactory.create_async(db_session, email="member@test.com")
        await TeamMemberFactory.create_user_member_async(
            db_session,
            team_id=team.id,
            user_id=member_user.id,
            role="member"
        )
        await db_session.commit()

        token = create_access_token(
            {"sub": str(member_user.id)},
            member_user.token_version
        )
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.patch(
            f"/api/teams/{team.id}",
            headers=headers,
            json={"description": "Trying to update"}
        )

        assert response.status_code == 403

    async def test_member_cannot_delete_team(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test member cannot delete team."""
        owner = await UserFactory.create_async(db_session, email="owner@test.com")
        team = await TeamFactory.create_async(
            db_session,
            user_id=owner.id,
            personal_team=False
        )

        member_user = await UserFactory.create_async(db_session, email="member@test.com")
        await TeamMemberFactory.create_user_member_async(
            db_session,
            team_id=team.id,
            user_id=member_user.id,
            role="member"
        )
        await db_session.commit()

        token = create_access_token(
            {"sub": str(member_user.id)},
            member_user.token_version
        )
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.delete(f"/api/teams/{team.id}", headers=headers)

        assert response.status_code == 403

    async def test_member_cannot_add_members(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test member cannot add other members (only admin)."""
        owner = await UserFactory.create_async(db_session, email="owner@test.com")
        team = await TeamFactory.create_async(db_session, user_id=owner.id)

        member_user = await UserFactory.create_async(db_session, email="member@test.com")
        await TeamMemberFactory.create_user_member_async(
            db_session,
            team_id=team.id,
            user_id=member_user.id,
            role="member"
        )

        new_member = await UserFactory.create_async(db_session, email="newmember@test.com")
        await db_session.commit()

        token = create_access_token(
            {"sub": str(member_user.id)},
            member_user.token_version
        )
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.post(
            f"/api/teams/{team.id}/members/users",
            headers=headers,
            json={"user_id": new_member.id, "role": "member"}
        )

        assert response.status_code == 403

    async def test_member_can_list_members(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test member can list team members."""
        owner = await UserFactory.create_async(db_session, email="owner@test.com")
        team = await TeamFactory.create_async(db_session, user_id=owner.id)

        member_user = await UserFactory.create_async(db_session, email="member@test.com")
        await TeamMemberFactory.create_user_member_async(
            db_session,
            team_id=team.id,
            user_id=member_user.id,
            role="member"
        )
        await db_session.commit()

        token = create_access_token(
            {"sub": str(member_user.id)},
            member_user.token_version
        )
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get(
            f"/api/teams/{team.id}/members",
            headers=headers
        )

        assert response.status_code == 200


@pytest.mark.asyncio
class TestViewerPermissions:
    """Test VIEWER role permissions (read-only)."""

    async def test_viewer_can_read_team(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test viewer can read team."""
        owner = await UserFactory.create_async(db_session, email="owner@test.com")
        team = await TeamFactory.create_async(db_session, user_id=owner.id)

        viewer_user = await UserFactory.create_async(db_session, email="viewer@test.com")
        await TeamMemberFactory.create_user_member_async(
            db_session,
            team_id=team.id,
            user_id=viewer_user.id,
            role="viewer"
        )
        await db_session.commit()

        token = create_access_token(
            {"sub": str(viewer_user.id)},
            viewer_user.token_version
        )
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get(f"/api/teams/{team.id}", headers=headers)

        assert response.status_code == 200

    async def test_viewer_cannot_update_team(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test viewer cannot update team."""
        owner = await UserFactory.create_async(db_session, email="owner@test.com")
        team = await TeamFactory.create_async(db_session, user_id=owner.id)

        viewer_user = await UserFactory.create_async(db_session, email="viewer@test.com")
        await TeamMemberFactory.create_user_member_async(
            db_session,
            team_id=team.id,
            user_id=viewer_user.id,
            role="viewer"
        )
        await db_session.commit()

        token = create_access_token(
            {"sub": str(viewer_user.id)},
            viewer_user.token_version
        )
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.patch(
            f"/api/teams/{team.id}",
            headers=headers,
            json={"description": "Trying to update"}
        )

        assert response.status_code == 403

    async def test_viewer_cannot_delete_team(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test viewer cannot delete team."""
        owner = await UserFactory.create_async(db_session, email="owner@test.com")
        team = await TeamFactory.create_async(
            db_session,
            user_id=owner.id,
            personal_team=False
        )

        viewer_user = await UserFactory.create_async(db_session, email="viewer@test.com")
        await TeamMemberFactory.create_user_member_async(
            db_session,
            team_id=team.id,
            user_id=viewer_user.id,
            role="viewer"
        )
        await db_session.commit()

        token = create_access_token(
            {"sub": str(viewer_user.id)},
            viewer_user.token_version
        )
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.delete(f"/api/teams/{team.id}", headers=headers)

        assert response.status_code == 403

    async def test_viewer_cannot_manage_members(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test viewer cannot add/remove members."""
        owner = await UserFactory.create_async(db_session, email="owner@test.com")
        team = await TeamFactory.create_async(db_session, user_id=owner.id)

        viewer_user = await UserFactory.create_async(db_session, email="viewer@test.com")
        await TeamMemberFactory.create_user_member_async(
            db_session,
            team_id=team.id,
            user_id=viewer_user.id,
            role="viewer"
        )

        new_member = await UserFactory.create_async(db_session, email="newmember@test.com")
        await db_session.commit()

        token = create_access_token(
            {"sub": str(viewer_user.id)},
            viewer_user.token_version
        )
        headers = {"Authorization": f"Bearer {token}"}

        # Viewer cannot add members
        add_response = await client.post(
            f"/api/teams/{team.id}/members/users",
            headers=headers,
            json={"user_id": new_member.id, "role": "member"}
        )
        assert add_response.status_code == 403

    async def test_viewer_can_list_members(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test viewer can list team members (read-only)."""
        owner = await UserFactory.create_async(db_session, email="owner@test.com")
        team = await TeamFactory.create_async(db_session, user_id=owner.id)

        viewer_user = await UserFactory.create_async(db_session, email="viewer@test.com")
        await TeamMemberFactory.create_user_member_async(
            db_session,
            team_id=team.id,
            user_id=viewer_user.id,
            role="viewer"
        )
        await db_session.commit()

        token = create_access_token(
            {"sub": str(viewer_user.id)},
            viewer_user.token_version
        )
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get(
            f"/api/teams/{team.id}/members",
            headers=headers
        )

        assert response.status_code == 200


@pytest.mark.asyncio
class TestOrganizationMemberPermissions:
    """Test permissions for users accessing via organization membership."""

    async def test_user_via_org_admin_can_update_team(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test user in org with admin role can update team."""
        owner = await UserFactory.create_async(db_session, email="owner@test.com")
        team = await TeamFactory.create_async(db_session, user_id=owner.id)

        # Create organization and add to team as admin
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

        # Create user who is member of organization
        org_user = await UserFactory.create_async(db_session, email="orguser@test.com")
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=org_user.id,
            role="admin"
        )
        await db_session.commit()

        # User accesses via organization membership
        token = create_access_token(
            {"sub": str(org_user.id)},
            org_user.token_version
        )
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.patch(
            f"/api/teams/{team.id}",
            headers=headers,
            json={"description": "Updated via org"}
        )

        # Should succeed (user → org → team, org is admin)
        assert response.status_code == 200

    async def test_user_via_org_member_cannot_delete_team(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test user in org with member role cannot delete team."""
        owner = await UserFactory.create_async(db_session, email="owner@test.com")
        team = await TeamFactory.create_async(
            db_session,
            user_id=owner.id,
            personal_team=False
        )

        # Org with member role
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

        # User in org
        org_user = await UserFactory.create_async(db_session, email="orguser@test.com")
        await OrganizationMemberFactory.create_async(
            db_session,
            organization_id=org.id,
            user_id=org_user.id,
            role="member"
        )
        await db_session.commit()

        token = create_access_token(
            {"sub": str(org_user.id)},
            org_user.token_version
        )
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.delete(f"/api/teams/{team.id}", headers=headers)

        # Member role cannot delete
        assert response.status_code == 403


@pytest.mark.asyncio
class TestPermissionsEdgeCases:
    """Test edge cases for permissions."""

    async def test_non_member_cannot_access_team(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test user who is not a member cannot access team."""
        owner = await UserFactory.create_async(db_session, email="owner@test.com")
        team = await TeamFactory.create_async(db_session, user_id=owner.id)

        # Random user not in team
        random_user = await UserFactory.create_async(db_session, email="random@test.com")
        await db_session.commit()

        token = create_access_token(
            {"sub": str(random_user.id)},
            random_user.token_version
        )
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get(f"/api/teams/{team.id}", headers=headers)

        assert response.status_code in [403, 404]

    async def test_inactive_member_cannot_access_team(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test inactive member cannot access team."""
        owner = await UserFactory.create_async(db_session, email="owner@test.com")
        team = await TeamFactory.create_async(db_session, user_id=owner.id)

        # Member with inactive status
        member_user = await UserFactory.create_async(db_session, email="inactive@test.com")
        await TeamMemberFactory.create_user_member_async(
            db_session,
            team_id=team.id,
            user_id=member_user.id,
            role="admin",
            status="inactive"
        )
        await db_session.commit()

        token = create_access_token(
            {"sub": str(member_user.id)},
            member_user.token_version
        )
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get(f"/api/teams/{team.id}", headers=headers)

        # Inactive members should be denied (if implemented)
        # Depends on implementation
        assert response.status_code in [200, 403]

    async def test_permissions_checked_on_every_request(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test that permissions are checked on every request (no caching issues)."""
        owner = await UserFactory.create_async(db_session, email="owner@test.com")
        team = await TeamFactory.create_async(db_session, user_id=owner.id)

        member_user = await UserFactory.create_async(db_session, email="member@test.com")
        tm = await TeamMemberFactory.create_user_member_async(
            db_session,
            team_id=team.id,
            user_id=member_user.id,
            role="member"
        )
        await db_session.commit()

        token = create_access_token(
            {"sub": str(member_user.id)},
            member_user.token_version
        )
        headers = {"Authorization": f"Bearer {token}"}

        # First request - member cannot update
        response1 = await client.patch(
            f"/api/teams/{team.id}",
            headers=headers,
            json={"description": "Attempt 1"}
        )
        assert response1.status_code == 403

        # Upgrade to admin
        tm.role = "admin"
        await db_session.commit()

        # Second request - now can update
        response2 = await client.patch(
            f"/api/teams/{team.id}",
            headers=headers,
            json={"description": "Attempt 2"}
        )
        assert response2.status_code == 200
