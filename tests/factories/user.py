"""
User factory for test data generation.
"""

import factory
from factory import fuzzy
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.core.security import get_password_hash


class UserFactory(factory.Factory):
    """
    Factory for User model.

    Default password: "Password123!" (hashed)
    """

    class Meta:
        model = User

    id = factory.Sequence(lambda n: n + 1)
    name = factory.Faker("name")
    email = factory.Faker("email")
    password = factory.LazyFunction(lambda: get_password_hash("Password123!"))
    two_factor_enabled = False
    two_factor_secret = None
    token_version = 1
    current_team_id = None  # Will be set after team creation

    @classmethod
    async def create_async(
        cls,
        db_session: AsyncSession,
        **kwargs
    ) -> User:
        """
        Create user in database asynchronously.

        Args:
            db_session: AsyncSession instance
            **kwargs: Override factory attributes

        Returns:
            User instance (committed to DB)

        Usage:
            user = await UserFactory.create_async(
                db_session,
                email="custom@test.com",
                name="Custom Name"
            )
        """
        instance = cls.build(**kwargs)
        db_session.add(instance)
        await db_session.flush()  # Get ID without committing transaction
        return instance

    @classmethod
    async def create_with_team_async(
        cls,
        db_session: AsyncSession,
        **kwargs
    ) -> User:
        """
        Create user with personal team.

        This mimics the real registration flow where a personal team
        is created automatically.

        Returns:
            User instance with current_team_id set
        """
        from tests.factories.team import TeamFactory

        user = await cls.create_async(db_session, **kwargs)

        # Create personal team
        team = await TeamFactory.create_async(
            db_session,
            user_id=user.id,
            name=f"{user.name}'s Team",
            personal_team=True
        )

        # Set current_team_id
        user.current_team_id = team.id
        await db_session.flush()

        return user
