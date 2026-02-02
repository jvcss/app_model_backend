"""
Smoke tests for critical endpoints.

Fast tests to detect critical breaks in CI/CD pipeline.
Target: <10 seconds total execution time.
"""

import pytest
from httpx import AsyncClient

from tests.factories.user import UserFactory


@pytest.mark.smoke
@pytest.mark.asyncio
class TestCriticalEndpoints:
    """Smoke tests for critical application endpoints."""

    async def test_register_endpoint(self, client: AsyncClient):
        """Test user registration endpoint is working."""
        response = await client.post(
            "/api/auth/register",
            json={
                "email": "smoke@test.com",
                "password": "SmokeTest123!",
                "name": "Smoke Test",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == "smoke@test.com"

    async def test_login_endpoint(self, client: AsyncClient, db_session):
        """Test login endpoint is working."""
        # Create user
        user = await UserFactory.create_with_team_async(
            db_session, email="login@test.com", password="LoginTest123!"
        )
        await db_session.commit()

        response = await client.post(
            "/api/auth/login",
            json={"email": "login@test.com", "password": "LoginTest123!"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    async def test_me_endpoint(self, client: AsyncClient, user, auth_headers):
        """Test /me endpoint returns user data."""
        response = await client.get("/api/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert data["user"]["id"] == user.id
        assert data["user"]["email"] == user.email

    async def test_teams_list_endpoint(self, client: AsyncClient, auth_headers):
        """Test teams list endpoint is accessible."""
        response = await client.get("/api/teams/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_organizations_list_endpoint(
        self, client: AsyncClient, auth_headers
    ):
        """Test organizations list endpoint is accessible."""
        response = await client.get("/api/organizations/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_unauthorized_access(self, client: AsyncClient):
        """Test that protected endpoints reject unauthorized access."""
        response = await client.get("/api/auth/me")

        assert response.status_code == 401

    async def test_invalid_credentials(self, client: AsyncClient):
        """Test login with invalid credentials is rejected."""
        response = await client.post(
            "/api/auth/login",
            json={"email": "nonexistent@test.com", "password": "wrong"},
        )

        assert response.status_code == 401


@pytest.mark.smoke
@pytest.mark.asyncio
class TestHealthChecks:
    """Smoke tests for application health."""

    async def test_registration_creates_personal_team(
        self, client: AsyncClient, db_session
    ):
        """Test that registration automatically creates personal team."""
        response = await client.post(
            "/api/auth/register",
            json={
                "email": "team@test.com",
                "password": "TeamTest123!",
                "name": "Team Test",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Get user info
        token = data["access_token"]
        me_response = await client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
        )

        assert me_response.status_code == 200
        me_data = me_response.json()
        assert me_data["user"]["current_team_id"] is not None

    async def test_create_and_retrieve_organization(
        self, client: AsyncClient, auth_headers
    ):
        """Test creating and retrieving an organization."""
        # Create organization
        create_response = await client.post(
            "/api/organizations/",
            headers=auth_headers,
            json={
                "name": "Smoke Test Org",
                "organization_type": "provider",
            },
        )

        assert create_response.status_code == 201
        org_id = create_response.json()["id"]

        # Retrieve organization
        get_response = await client.get(
            f"/api/organizations/{org_id}", headers=auth_headers
        )

        assert get_response.status_code == 200
        data = get_response.json()
        assert data["name"] == "Smoke Test Org"

    async def test_token_validation(self, client: AsyncClient, user):
        """Test that JWT token validation works correctly."""
        from app.core.security import create_access_token

        # Valid token
        valid_token = create_access_token(
            {"sub": str(user.id)}, user.token_version
        )
        response = await client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {valid_token}"}
        )
        assert response.status_code == 200

        # Invalid token
        response = await client.get(
            "/api/auth/me", headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401
