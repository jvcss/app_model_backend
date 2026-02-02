"""
OrganizationMember factory for test data generation.
"""

import factory
from factory import fuzzy
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization_member import OrganizationMember


class OrganizationMemberFactory(factory.Factory):
    """
    Factory for OrganizationMember model.

    Links users to organizations with specific roles.
    """

    class Meta:
        model = OrganizationMember

    id = factory.Sequence(lambda n: n + 1)
    organization_id = None  # Must be set
    user_id = None  # Must be set
    role = fuzzy.FuzzyChoice(["admin", "member"])
    status = "active"
    joined_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))

    @classmethod
    async def create_async(
        cls,
        db_session: AsyncSession,
        **kwargs
    ) -> OrganizationMember:
        """
        Create organization member in database asynchronously.

        Args:
            db_session: AsyncSession instance
            **kwargs: Override factory attributes (organization_id, user_id required)

        Returns:
            OrganizationMember instance

        Usage:
            om = await OrganizationMemberFactory.create_async(
                db_session,
                organization_id=org.id,
                user_id=user.id,
                role="admin"
            )
        """
        required_fields = ["organization_id", "user_id"]
        for field in required_fields:
            if field not in kwargs:
                raise ValueError(f"{field} is required for OrganizationMemberFactory")

        instance = cls.build(**kwargs)
        db_session.add(instance)
        await db_session.flush()
        return instance
