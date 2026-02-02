"""
End-to-end test for team collaboration flow with multiple users.

Tests complete multi-user team workflows.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories.organization import OrganizationFactory
from tests.factories.user import UserFactory


@pytest.mark.e2e
@pytest.mark.asyncio
class TestTeamCollaborationFlow:
    """Complete team collaboration flow with multiple users and organizations."""

    async def test_complete_team_collaboration_flow(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """
        Test complete team collaboration scenario:
        1. User A creates team
        2. User B registers
        3. User A invites User B to team
        4. User B accepts and joins team
        5. User A creates organization
        6. User A adds organization to team
        7. Both users can see team and organization
        8. User B (member) cannot delete team
        9. User A (owner) can delete team
        """
        # Step 1: User A creates team
        user_a = await UserFactory.create_with_team_async(
            db_session, email="usera@test.com", password="UserA123!"
        )
        await db_session.commit()

        login_a = await client.post(
            "/api/auth/login",
            json={"email": "usera@test.com", "password": "UserA123!"},
        )
        token_a = login_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        team_response = await client.post(
            "/api/teams/",
            headers=headers_a,
            json={"name": "Collaboration Team"},
        )

        assert team_response.status_code == 201
        team_id = team_response.json()["id"]

        # Step 2: User B registers
        user_b = await UserFactory.create_with_team_async(
            db_session, email="userb@test.com", password="UserB123!"
        )
        await db_session.commit()

        login_b = await client.post(
            "/api/auth/login",
            json={"email": "userb@test.com", "password": "UserB123!"},
        )
        token_b = login_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Step 3: User A invites User B to team
        invite_response = await client.post(
            f"/api/teams/{team_id}/members/users",
            headers=headers_a,
            json={"user_id": user_b.id, "role": "member"},
        )

        assert invite_response.status_code == 201

        # Step 4: User B can see the team
        teams_b_response = await client.get("/api/teams/", headers=headers_b)
        teams_b = teams_b_response.json()

        # User B should see personal team + invited team
        assert len(teams_b) >= 2
        assert any(t["id"] == team_id for t in teams_b)

        # Step 5: User A creates organization
        org_response = await client.post(
            "/api/organizations/",
            headers=headers_a,
            json={
                "name": "Collaboration Org",
                "organization_type": "provider",
            },
        )

        assert org_response.status_code == 201
        org_id = org_response.json()["id"]

        # Step 6: User A adds organization to team
        add_org_response = await client.post(
            f"/api/teams/{team_id}/members/organizations",
            headers=headers_a,
            json={"organization_id": org_id, "role": "member"},
        )

        assert add_org_response.status_code == 201

        # Step 7: Both users can see team members
        members_a_response = await client.get(
            f"/api/teams/{team_id}/members", headers=headers_a
        )
        members_a = members_a_response.json()

        members_b_response = await client.get(
            f"/api/teams/{team_id}/members", headers=headers_b
        )
        members_b = members_b_response.json()

        # Should have User A (owner), User B (member), Organization (member)
        assert len(members_a) == 3
        assert len(members_b) == 3

        # Step 8: User B (member) cannot delete team
        delete_b_response = await client.delete(
            f"/api/teams/{team_id}", headers=headers_b
        )

        assert delete_b_response.status_code == 403

        # Step 9: User A (owner) can delete team
        delete_a_response = await client.delete(
            f"/api/teams/{team_id}", headers=headers_a
        )

        assert delete_a_response.status_code == 200

    async def test_organization_member_permissions_flow(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """
        Test that users get permissions through organization membership:
        1. User A creates team and organization
        2. User A adds organization to team with admin role
        3. User B joins organization as member
        4. User B should have access to team through organization
        """
        # Step 1: User A setup
        user_a = await UserFactory.create_with_team_async(
            db_session, email="owner@test.com", password="Owner123!"
        )
        await db_session.commit()

        login_a = await client.post(
            "/api/auth/login",
            json={"email": "owner@test.com", "password": "Owner123!"},
        )
        token_a = login_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # Create team
        team_response = await client.post(
            "/api/teams/", headers=headers_a, json={"name": "Org Team"}
        )
        team_id = team_response.json()["id"]

        # Create organization
        org_response = await client.post(
            "/api/organizations/",
            headers=headers_a,
            json={"name": "Test Org", "organization_type": "provider"},
        )
        org_id = org_response.json()["id"]

        # Step 2: Add organization to team with admin role
        await client.post(
            f"/api/teams/{team_id}/members/organizations",
            headers=headers_a,
            json={"organization_id": org_id, "role": "admin"},
        )

        # Step 3: User B joins organization
        user_b = await UserFactory.create_with_team_async(
            db_session, email="member@test.com", password="Member123!"
        )
        await db_session.commit()

        # User A adds User B to organization
        await client.post(
            f"/api/organizations/{org_id}/members",
            headers=headers_a,
            json={"user_id": user_b.id, "role": "member"},
        )

        # Step 4: User B should have access through organization
        login_b = await client.post(
            "/api/auth/login",
            json={"email": "member@test.com", "password": "Member123!"},
        )
        token_b = login_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # User B can see the team
        teams_response = await client.get("/api/teams/", headers=headers_b)
        teams = teams_response.json()
        assert any(t["id"] == team_id for t in teams)

        # User B can view team details
        team_detail = await client.get(
            f"/api/teams/{team_id}", headers=headers_b
        )
        assert team_detail.status_code == 200

    async def test_multi_organization_collaboration(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """
        Test collaboration between multiple organizations:
        1. Create Provider organization
        2. Create Client organization
        3. Create shared team
        4. Add both organizations to team
        5. Verify both can collaborate
        """
        # Step 1: Create user and Provider organization
        user = await UserFactory.create_with_team_async(
            db_session, email="collab@test.com", password="Collab123!"
        )
        await db_session.commit()

        login = await client.post(
            "/api/auth/login",
            json={"email": "collab@test.com", "password": "Collab123!"},
        )
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        provider_response = await client.post(
            "/api/organizations/",
            headers=headers,
            json={"name": "Provider Co", "organization_type": "provider"},
        )
        provider_id = provider_response.json()["id"]

        # Step 2: Create Client organization
        client_response = await client.post(
            "/api/organizations/",
            headers=headers,
            json={"name": "Client Co", "organization_type": "client"},
        )
        client_id = client_response.json()["id"]

        # Step 3: Create shared team
        team_response = await client.post(
            "/api/teams/", headers=headers, json={"name": "Shared Project"}
        )
        team_id = team_response.json()["id"]

        # Step 4: Add both organizations to team
        await client.post(
            f"/api/teams/{team_id}/members/organizations",
            headers=headers,
            json={"organization_id": provider_id, "role": "admin"},
        )

        await client.post(
            f"/api/teams/{team_id}/members/organizations",
            headers=headers,
            json={"organization_id": client_id, "role": "member"},
        )

        # Step 5: Verify team structure
        members_response = await client.get(
            f"/api/teams/{team_id}/members", headers=headers
        )
        members = members_response.json()

        # Should have user + 2 organizations
        assert len(members) == 3

        org_members = [m for m in members if m["member_type"] == "organization"]
        assert len(org_members) == 2

        org_ids = {m["organization_id"] for m in org_members}
        assert provider_id in org_ids
        assert client_id in org_ids

    async def test_role_hierarchy_enforcement(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """
        Test role hierarchy in team collaboration:
        1. Owner can do everything
        2. Admin can manage members but not delete team
        3. Member has limited permissions
        4. Viewer can only read
        """
        # Setup: Create team with multiple members at different roles
        owner = await UserFactory.create_with_team_async(
            db_session, email="owner@test.com", password="Owner123!"
        )
        admin = await UserFactory.create_with_team_async(
            db_session, email="admin@test.com", password="Admin123!"
        )
        member = await UserFactory.create_with_team_async(
            db_session, email="member@test.com", password="Member123!"
        )
        viewer = await UserFactory.create_with_team_async(
            db_session, email="viewer@test.com", password="Viewer123!"
        )
        await db_session.commit()

        # Owner login and create team
        login_owner = await client.post(
            "/api/auth/login",
            json={"email": "owner@test.com", "password": "Owner123!"},
        )
        token_owner = login_owner.json()["access_token"]
        headers_owner = {"Authorization": f"Bearer {token_owner}"}

        team_response = await client.post(
            "/api/teams/",
            headers=headers_owner,
            json={"name": "Hierarchy Test"},
        )
        team_id = team_response.json()["id"]

        # Add members with different roles
        await client.post(
            f"/api/teams/{team_id}/members/users",
            headers=headers_owner,
            json={"user_id": admin.id, "role": "admin"},
        )
        await client.post(
            f"/api/teams/{team_id}/members/users",
            headers=headers_owner,
            json={"user_id": member.id, "role": "member"},
        )
        await client.post(
            f"/api/teams/{team_id}/members/users",
            headers=headers_owner,
            json={"user_id": viewer.id, "role": "viewer"},
        )

        # Get tokens for other users
        login_admin = await client.post(
            "/api/auth/login",
            json={"email": "admin@test.com", "password": "Admin123!"},
        )
        headers_admin = {
            "Authorization": f"Bearer {login_admin.json()['access_token']}"
        }

        login_member = await client.post(
            "/api/auth/login",
            json={"email": "member@test.com", "password": "Member123!"},
        )
        headers_member = {
            "Authorization": f"Bearer {login_member.json()['access_token']}"
        }

        login_viewer = await client.post(
            "/api/auth/login",
            json={"email": "viewer@test.com", "password": "Viewer123!"},
        )
        headers_viewer = {
            "Authorization": f"Bearer {login_viewer.json()['access_token']}"
        }

        # Test 1: Owner can delete team
        # (Skip actual deletion to continue testing)

        # Test 2: Admin cannot delete team
        delete_admin = await client.delete(
            f"/api/teams/{team_id}", headers=headers_admin
        )
        assert delete_admin.status_code == 403

        # Test 3: Member cannot update team
        update_member = await client.put(
            f"/api/teams/{team_id}",
            headers=headers_member,
            json={"name": "Changed Name"},
        )
        assert update_member.status_code == 403

        # Test 4: Viewer can read but not write
        read_viewer = await client.get(
            f"/api/teams/{team_id}", headers=headers_viewer
        )
        assert read_viewer.status_code == 200

        update_viewer = await client.put(
            f"/api/teams/{team_id}",
            headers=headers_viewer,
            json={"name": "Changed"},
        )
        assert update_viewer.status_code == 403
