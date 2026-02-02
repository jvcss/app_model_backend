"""
Team factory for test data generation.
"""

import factory
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.team import Team


class TeamFactory(factory.Factory):
    """
    Factory for Team model.
    """

    class Meta:
        model = Team

    id = factory.Sequence(lambda n: n + 1)
    name = factory.Faker("company")
    description = factory.Faker("catch_phrase")
    personal_team = False
    archived = False
    archived_at = None
    user_id = None  # Must be set when creating

    @classmethod
    async def create_async(
        cls,
        db_session: AsyncSession,
        **kwargs
    ) -> Team:
        """
        Create team in database asynchronously.

        Args:
            db_session: AsyncSession instance
            **kwargs: Override factory attributes (user_id is required)

        Returns:
            Team instance

        Usage:
            team = await TeamFactory.create_async(
                db_session,
                user_id=user.id,
                name="My Team"
            )
        """
        if "user_id" not in kwargs:
            raise ValueError("user_id is required for TeamFactory")

        instance = cls.build(**kwargs)
        db_session.add(instance)
        await db_session.flush()
        return instance
