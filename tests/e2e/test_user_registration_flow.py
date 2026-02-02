"""
End-to-end test for complete user registration flow.

Tests the full journey from registration to team collaboration.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.e2e
@pytest.mark.asyncio
class TestUserRegistrationFlow:
    """Complete user registration and setup flow."""

    async def test_complete_registration_flow(self, client: AsyncClient):
        """
        Test complete user registration flow:
        1. Register new user
        2. Verify user data and personal team
        3. Create organization
        4. Create team
        5. Add organization to team
        6. Verify team structure
        """
        # Step 1: Register new user
        register_response = await client.post(
            "/api/auth/register",
            json={
                "email": "newuser@test.com",
                "password": "NewUser123!",
                "name": "New User",
            },
        )

        assert register_response.status_code == 200
        register_data = register_response.json()
        assert "access_token" in register_data
        assert register_data["user"]["email"] == "newuser@test.com"

        token = register_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Step 2: Verify user data and personal team
        me_response = await client.get("/api/auth/me", headers=headers)
        assert me_response.status_code == 200
        me_data = me_response.json()

        user_id = me_data["user"]["id"]
        personal_team_id = me_data["user"]["current_team_id"]
        assert personal_team_id is not None

        # Verify personal team exists
        teams_response = await client.get("/api/teams/", headers=headers)
        assert teams_response.status_code == 200
        teams = teams_response.json()
        assert len(teams) >= 1
        assert any(t["id"] == personal_team_id for t in teams)

        # Step 3: Create organization
        org_response = await client.post(
            "/api/organizations/",
            headers=headers,
            json={
                "name": "E2E Test Organization",
                "organization_type": "provider",
            },
        )

        assert org_response.status_code == 201
        org_data = org_response.json()
        org_id = org_data["id"]
        assert org_data["name"] == "E2E Test Organization"

        # Verify user is admin of organization
        org_members_response = await client.get(
            f"/api/organizations/{org_id}/members", headers=headers
        )
        assert org_members_response.status_code == 200
        org_members = org_members_response.json()
        assert len(org_members) == 1
        assert org_members[0]["user_id"] == user_id
        assert org_members[0]["role"] == "admin"

        # Step 4: Create new team
        team_response = await client.post(
            "/api/teams/",
            headers=headers,
            json={"name": "E2E Test Team"},
        )

        assert team_response.status_code == 201
        team_data = team_response.json()
        team_id = team_data["id"]
        assert team_data["name"] == "E2E Test Team"

        # Step 5: Add organization to team
        add_org_response = await client.post(
            f"/api/teams/{team_id}/members/organizations",
            headers=headers,
            json={
                "organization_id": org_id,
                "role": "member",
            },
        )

        assert add_org_response.status_code == 201

        # Step 6: Verify team structure
        team_members_response = await client.get(
            f"/api/teams/{team_id}/members", headers=headers
        )
        assert team_members_response.status_code == 200
        team_members = team_members_response.json()

        # Should have user (owner) + organization (member)
        assert len(team_members) == 2

        user_member = next(
            (m for m in team_members if m["member_type"] == "user"), None
        )
        org_member = next(
            (m for m in team_members if m["member_type"] == "organization"),
            None,
        )

        assert user_member is not None
        assert user_member["user_id"] == user_id
        assert user_member["role"] == "owner"

        assert org_member is not None
        assert org_member["organization_id"] == org_id
        assert org_member["role"] == "member"

    async def test_registration_with_immediate_team_switch(
        self, client: AsyncClient
    ):
        """
        Test user can switch teams immediately after registration:
        1. Register
        2. Create new team
        3. Switch to new team
        4. Verify current team changed
        """
        # Step 1: Register
        register_response = await client.post(
            "/api/auth/register",
            json={
                "email": "switcher@test.com",
                "password": "Switcher123!",
                "name": "Team Switcher",
            },
        )

        assert register_response.status_code == 200
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Get initial team
        me_response = await client.get("/api/auth/me", headers=headers)
        initial_team_id = me_response.json()["user"]["current_team_id"]

        # Step 2: Create new team
        team_response = await client.post(
            "/api/teams/",
            headers=headers,
            json={"name": "New Team"},
        )

        assert team_response.status_code == 201
        new_team_id = team_response.json()["id"]
        assert new_team_id != initial_team_id

        # Step 3: Switch to new team
        switch_response = await client.post(
            f"/api/teams/{new_team_id}/switch", headers=headers
        )

        assert switch_response.status_code == 200

        # Step 4: Verify current team changed
        me_response = await client.get("/api/auth/me", headers=headers)
        current_team_id = me_response.json()["user"]["current_team_id"]
        assert current_team_id == new_team_id

    async def test_registration_with_multiple_organizations(
        self, client: AsyncClient
    ):
        """
        Test user can create and manage multiple organizations:
        1. Register
        2. Create provider organization
        3. Create client organization
        4. Verify both exist
        5. Verify user is admin of both
        """
        # Step 1: Register
        register_response = await client.post(
            "/api/auth/register",
            json={
                "email": "multiorg@test.com",
                "password": "MultiOrg123!",
                "name": "Multi Org User",
            },
        )

        assert register_response.status_code == 200
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Step 2: Create provider organization
        provider_response = await client.post(
            "/api/organizations/",
            headers=headers,
            json={
                "name": "Provider Org",
                "organization_type": "provider",
            },
        )

        assert provider_response.status_code == 201
        provider_id = provider_response.json()["id"]

        # Step 3: Create client organization
        client_response = await client.post(
            "/api/organizations/",
            headers=headers,
            json={
                "name": "Client Org",
                "organization_type": "client",
            },
        )

        assert client_response.status_code == 201
        client_id = client_response.json()["id"]

        # Step 4: Verify both exist
        orgs_response = await client.get("/api/organizations/", headers=headers)
        assert orgs_response.status_code == 200
        orgs = orgs_response.json()
        assert len(orgs) == 2

        org_ids = {org["id"] for org in orgs}
        assert provider_id in org_ids
        assert client_id in org_ids

        # Step 5: Verify user is admin of both
        me_response = await client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["user"]["id"]

        # Check provider membership
        provider_members_response = await client.get(
            f"/api/organizations/{provider_id}/members", headers=headers
        )
        provider_members = provider_members_response.json()
        assert any(
            m["user_id"] == user_id and m["role"] == "admin"
            for m in provider_members
        )

        # Check client membership
        client_members_response = await client.get(
            f"/api/organizations/{client_id}/members", headers=headers
        )
        client_members = client_members_response.json()
        assert any(
            m["user_id"] == user_id and m["role"] == "admin"
            for m in client_members
        )
