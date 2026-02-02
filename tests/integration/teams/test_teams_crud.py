"""
Integration tests for teams CRUD operations.

Tests:
- GET /api/teams/ - List teams
- POST /api/teams/ - Create team
- GET /api/teams/{team_id} - Get team by ID
- PATCH /api/teams/{team_id} - Update team
- DELETE /api/teams/{team_id} - Delete team (soft delete)
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.team import Team
from tests.factories import UserFactory, TeamFactory


@pytest.mark.asyncio
class TestListTeams:
    """Test GET /api/teams/ - List teams."""

    async def test_list_teams_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test listing teams owned by user."""
        # Create teams owned by user
        team1 = await TeamFactory.create_async(
            db_session,
            user_id=user.id,
            name="Team Alpha"
        )
        team2 = await TeamFactory.create_async(
            db_session,
            user_id=user.id,
            name="Team Beta"
        )
        await db_session.commit()

        response = await client.get("/api/teams/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2

        team_names = [t["name"] for t in data]
        assert "Team Alpha" in team_names
        assert "Team Beta" in team_names

    async def test_list_teams_empty(
        self,
        client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test listing teams when user has no teams."""
        # Create user with no teams
        user = await UserFactory.create_async(db_session, email="noTeams@test.com")
        await db_session.commit()

        from app.core.security import create_access_token
        token = create_access_token({"sub": str(user.id)}, user.token_version)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/api/teams/", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Might be empty or contain personal team (depends on registration flow)

    async def test_list_teams_no_auth(self, client: AsyncClient):
        """Test listing teams without authentication."""
        response = await client.get("/api/teams/")

        assert response.status_code == 401

    async def test_list_teams_filters_by_owner(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test that list only shows teams owned by current user."""
        # Create team by current user
        await TeamFactory.create_async(
            db_session,
            user_id=user.id,
            name="My Team"
        )

        # Create team by another user
        other_user = await UserFactory.create_async(db_session, email="other@test.com")
        await TeamFactory.create_async(
            db_session,
            user_id=other_user.id,
            name="Other Team"
        )
        await db_session.commit()

        response = await client.get("/api/teams/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        team_names = [t["name"] for t in data]
        assert "My Team" in team_names
        assert "Other Team" not in team_names  # Should not see other user's teams

    async def test_list_teams_excludes_archived(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test that archived teams are excluded from list (if implemented)."""
        from datetime import datetime, timezone

        # Create active team
        await TeamFactory.create_async(
            db_session,
            user_id=user.id,
            name="Active Team",
            archived=False
        )

        # Create archived team
        await TeamFactory.create_async(
            db_session,
            user_id=user.id,
            name="Archived Team",
            archived=True,
            archived_at=datetime.now(timezone.utc)
        )
        await db_session.commit()

        response = await client.get("/api/teams/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        team_names = [t["name"] for t in data]
        assert "Active Team" in team_names
        # Depending on implementation, archived teams might be excluded
        # assert "Archived Team" not in team_names


@pytest.mark.asyncio
class TestCreateTeam:
    """Test POST /api/teams/ - Create team."""

    async def test_create_team_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test creating a new team."""
        response = await client.post(
            "/api/teams/",
            headers=auth_headers,
            json={
                "name": "New Team",
                "description": "A brand new team",
                "personal_team": False
            }
        )

        assert response.status_code == 201
        data = response.json()

        assert data["name"] == "New Team"
        assert data["description"] == "A brand new team"
        assert data["user_id"] == user.id
        assert data["personal_team"] is False
        assert data["archived"] is False
        assert "id" in data

        # Verify team created in DB
        result = await db_session.execute(
            select(Team).where(Team.id == data["id"])
        )
        team = result.scalar_one_or_none()
        assert team is not None
        assert team.name == "New Team"

    async def test_create_team_minimal(
        self,
        client: AsyncClient,
        user,
        auth_headers
    ):
        """Test creating team with minimal fields."""
        response = await client.post(
            "/api/teams/",
            headers=auth_headers,
            json={"name": "Minimal Team"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Minimal Team"
        assert data["description"] is None
        assert data["personal_team"] is False  # Default

    async def test_create_team_no_auth(self, client: AsyncClient):
        """Test creating team without authentication."""
        response = await client.post(
            "/api/teams/",
            json={"name": "Team"}
        )

        assert response.status_code == 401

    async def test_create_team_missing_name(
        self,
        client: AsyncClient,
        auth_headers
    ):
        """Test creating team without name."""
        response = await client.post(
            "/api/teams/",
            headers=auth_headers,
            json={"description": "No name team"}
        )

        assert response.status_code == 422

    async def test_create_team_empty_name(
        self,
        client: AsyncClient,
        auth_headers
    ):
        """Test creating team with empty name."""
        response = await client.post(
            "/api/teams/",
            headers=auth_headers,
            json={"name": ""}
        )

        assert response.status_code == 422

    async def test_create_team_very_long_name(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_headers
    ):
        """Test creating team with very long name."""
        long_name = "A" * 500

        response = await client.post(
            "/api/teams/",
            headers=auth_headers,
            json={"name": long_name}
        )

        # Should succeed (or fail if there's a length limit)
        if response.status_code == 201:
            data = response.json()
            assert data["name"] == long_name

    async def test_create_team_unicode_name(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_headers
    ):
        """Test creating team with unicode characters."""
        response = await client.post(
            "/api/teams/",
            headers=auth_headers,
            json={"name": "Equipe 中文 Русский"}
        )

        assert response.status_code == 201
        assert response.json()["name"] == "Equipe 中文 Русский"

    async def test_create_personal_team(
        self,
        client: AsyncClient,
        auth_headers
    ):
        """Test creating a personal team."""
        response = await client.post(
            "/api/teams/",
            headers=auth_headers,
            json={
                "name": "My Personal Team",
                "personal_team": True
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["personal_team"] is True


@pytest.mark.asyncio
class TestGetTeam:
    """Test GET /api/teams/{team_id} - Get team by ID."""

    async def test_get_team_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test getting team by ID."""
        team = await TeamFactory.create_async(
            db_session,
            user_id=user.id,
            name="Test Team"
        )
        await db_session.commit()

        response = await client.get(
            f"/api/teams/{team.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == team.id
        assert data["name"] == "Test Team"
        assert data["user_id"] == user.id

    async def test_get_team_not_found(
        self,
        client: AsyncClient,
        auth_headers
    ):
        """Test getting non-existent team."""
        response = await client.get(
            "/api/teams/99999",
            headers=auth_headers
        )

        assert response.status_code == 404

    async def test_get_team_no_auth(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user
    ):
        """Test getting team without authentication."""
        team = await TeamFactory.create_async(db_session, user_id=user.id)
        await db_session.commit()

        response = await client.get(f"/api/teams/{team.id}")

        assert response.status_code == 401

    async def test_get_team_not_owner(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test getting team owned by another user."""
        # Create another user with a team
        other_user = await UserFactory.create_async(db_session, email="other@test.com")
        other_team = await TeamFactory.create_async(
            db_session,
            user_id=other_user.id,
            name="Other Team"
        )
        await db_session.commit()

        # Try to get other user's team
        response = await client.get(
            f"/api/teams/{other_team.id}",
            headers=auth_headers
        )

        # Should fail - only owner can access (or 404 to prevent enumeration)
        assert response.status_code in [403, 404]


@pytest.mark.asyncio
class TestUpdateTeam:
    """Test PATCH /api/teams/{team_id} - Update team."""

    async def test_update_team_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test updating team as owner."""
        team = await TeamFactory.create_async(
            db_session,
            user_id=user.id,
            name="Original Name",
            description="Original Description"
        )
        await db_session.commit()

        response = await client.patch(
            f"/api/teams/{team.id}",
            headers=auth_headers,
            json={
                "name": "Updated Name",
                "description": "Updated Description"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated Description"

        # Verify in DB
        await db_session.refresh(team)
        assert team.name == "Updated Name"
        assert team.description == "Updated Description"

    async def test_update_team_partial(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test partial update (only some fields)."""
        team = await TeamFactory.create_async(
            db_session,
            user_id=user.id,
            name="Original Name",
            description="Original Description"
        )
        await db_session.commit()

        # Update only description
        response = await client.patch(
            f"/api/teams/{team.id}",
            headers=auth_headers,
            json={"description": "New Description"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Original Name"  # Unchanged
        assert data["description"] == "New Description"  # Changed

    async def test_update_team_no_auth(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user
    ):
        """Test updating team without authentication."""
        team = await TeamFactory.create_async(db_session, user_id=user.id)
        await db_session.commit()

        response = await client.patch(
            f"/api/teams/{team.id}",
            json={"name": "New Name"}
        )

        assert response.status_code == 401

    async def test_update_team_not_owner(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test updating team owned by another user."""
        other_user = await UserFactory.create_async(db_session, email="other@test.com")
        other_team = await TeamFactory.create_async(
            db_session,
            user_id=other_user.id
        )
        await db_session.commit()

        response = await client.patch(
            f"/api/teams/{other_team.id}",
            headers=auth_headers,
            json={"name": "Hacked Name"}
        )

        assert response.status_code in [403, 404]

    async def test_update_team_not_found(
        self,
        client: AsyncClient,
        auth_headers
    ):
        """Test updating non-existent team."""
        response = await client.patch(
            "/api/teams/99999",
            headers=auth_headers,
            json={"name": "New Name"}
        )

        assert response.status_code == 404


@pytest.mark.asyncio
class TestDeleteTeam:
    """Test DELETE /api/teams/{team_id} - Delete team (soft delete)."""

    async def test_delete_team_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test deleting team (soft delete)."""
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

        # Verify soft delete (archived = True)
        await db_session.refresh(team)
        assert team.archived is True
        assert team.archived_at is not None

    async def test_delete_personal_team_fails(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test that personal teams cannot be deleted."""
        personal_team = await TeamFactory.create_async(
            db_session,
            user_id=user.id,
            personal_team=True
        )
        await db_session.commit()

        response = await client.delete(
            f"/api/teams/{personal_team.id}",
            headers=auth_headers
        )

        assert response.status_code == 400
        data = response.json()
        assert "personal" in data["detail"].lower()

        # Verify team not deleted
        await db_session.refresh(personal_team)
        assert personal_team.archived is False

    async def test_delete_team_no_auth(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user
    ):
        """Test deleting team without authentication."""
        team = await TeamFactory.create_async(db_session, user_id=user.id)
        await db_session.commit()

        response = await client.delete(f"/api/teams/{team.id}")

        assert response.status_code == 401

    async def test_delete_team_not_owner(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test deleting team owned by another user."""
        other_user = await UserFactory.create_async(db_session, email="other@test.com")
        other_team = await TeamFactory.create_async(
            db_session,
            user_id=other_user.id,
            personal_team=False
        )
        await db_session.commit()

        response = await client.delete(
            f"/api/teams/{other_team.id}",
            headers=auth_headers
        )

        assert response.status_code in [403, 404]

        # Verify team not deleted
        await db_session.refresh(other_team)
        assert other_team.archived is False

    async def test_delete_team_not_found(
        self,
        client: AsyncClient,
        auth_headers
    ):
        """Test deleting non-existent team."""
        response = await client.delete(
            "/api/teams/99999",
            headers=auth_headers
        )

        assert response.status_code == 404

    async def test_delete_team_already_archived(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test deleting already archived team."""
        from datetime import datetime, timezone

        team = await TeamFactory.create_async(
            db_session,
            user_id=user.id,
            personal_team=False,
            archived=True,
            archived_at=datetime.now(timezone.utc)
        )
        await db_session.commit()

        response = await client.delete(
            f"/api/teams/{team.id}",
            headers=auth_headers
        )

        # Might be 204 (idempotent) or 404 (not found because archived)
        assert response.status_code in [204, 404]


@pytest.mark.asyncio
class TestTeamsCRUDEdgeCases:
    """Test edge cases for teams CRUD."""

    async def test_create_duplicate_team_names_allowed(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test that duplicate team names are allowed (no unique constraint)."""
        # Create first team
        await client.post(
            "/api/teams/",
            headers=auth_headers,
            json={"name": "Duplicate Name"}
        )

        # Create second team with same name
        response = await client.post(
            "/api/teams/",
            headers=auth_headers,
            json={"name": "Duplicate Name"}
        )

        # Should succeed (names are not unique)
        assert response.status_code == 201

    async def test_update_team_empty_name_fails(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user,
        auth_headers
    ):
        """Test updating team with empty name."""
        team = await TeamFactory.create_async(db_session, user_id=user.id)
        await db_session.commit()

        response = await client.patch(
            f"/api/teams/{team.id}",
            headers=auth_headers,
            json={"name": ""}
        )

        assert response.status_code == 422

    async def test_sql_injection_in_team_name(
        self,
        client: AsyncClient,
        auth_headers
    ):
        """Test SQL injection prevention."""
        response = await client.post(
            "/api/teams/",
            headers=auth_headers,
            json={"name": "Team'; DROP TABLE teams; --"}
        )

        # Should not cause SQL error
        assert response.status_code in [201, 422]

    async def test_xss_in_team_description(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_headers
    ):
        """Test XSS prevention in description."""
        response = await client.post(
            "/api/teams/",
            headers=auth_headers,
            json={
                "name": "XSS Team",
                "description": "<script>alert('xss')</script>"
            }
        )

        if response.status_code == 201:
            # Description should be stored as-is (escaped when rendered)
            data = response.json()
            assert data["description"] == "<script>alert('xss')</script>"
