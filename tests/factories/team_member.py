"""
TeamMember factory for test data generation.

Handles polymorphic team members (user or organization).
"""

import factory
from factory import fuzzy
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.team_member import TeamMember


class TeamMemberFactory(factory.Factory):
    """
    Factory for polymorphic TeamMember model.

    TeamMember can reference either a User or an Organization.
    """

    class Meta:
        model = TeamMember

    id = factory.Sequence(lambda n: n + 1)
    team_id = None  # Must be set
    member_type = "user"  # or "organization"
    member_id = None  # Must be set (user.id or organization.id)
    role = fuzzy.FuzzyChoice(["admin", "member", "viewer"])
    status = "active"
    invited_by = None
    invited_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    joined_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))

    @classmethod
    async def create_async(
        cls,
        db_session: AsyncSession,
        **kwargs
    ) -> TeamMember:
        """
        Create team member in database asynchronously.

        Args:
            db_session: AsyncSession instance
            **kwargs: Override factory attributes (team_id, member_type, member_id required)

        Returns:
            TeamMember instance

        Usage:
            # Add user to team
            tm = await TeamMemberFactory.create_async(
                db_session,
                team_id=team.id,
                member_type="user",
                member_id=user.id,
                role="member"
            )

            # Add organization to team
            tm = await TeamMemberFactory.create_async(
                db_session,
                team_id=team.id,
                member_type="organization",
                member_id=org.id,
                role="admin"
            )
        """
        required_fields = ["team_id", "member_type", "member_id"]
        for field in required_fields:
            if field not in kwargs:
                raise ValueError(f"{field} is required for TeamMemberFactory")

        if kwargs["member_type"] not in ["user", "organization"]:
            raise ValueError("member_type must be 'user' or 'organization'")

        instance = cls.build(**kwargs)
        db_session.add(instance)
        await db_session.flush()
        return instance

    @classmethod
    async def create_user_member_async(
        cls,
        db_session: AsyncSession,
        team_id: int,
        user_id: int,
        role: str = "member",
        **kwargs
    ) -> TeamMember:
        """
        Convenience method to add user to team.
        """
        return await cls.create_async(
            db_session,
            team_id=team_id,
            member_type="user",
            member_id=user_id,
            role=role,
            **kwargs
        )

    @classmethod
    async def create_org_member_async(
        cls,
        db_session: AsyncSession,
        team_id: int,
        organization_id: int,
        role: str = "member",
        **kwargs
    ) -> TeamMember:
        """
        Convenience method to add organization to team.
        """
        return await cls.create_async(
            db_session,
            team_id=team_id,
            member_type="organization",
            member_id=organization_id,
            role=role,
            **kwargs
        )
