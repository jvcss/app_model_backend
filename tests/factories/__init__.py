"""
Data factories for test data generation.

Factories use factory-boy to create realistic test data with sensible defaults.
All factories support async creation via create_async() method.

Usage:
    from tests.factories import UserFactory, TeamFactory

    # Create user
    user = await UserFactory.create_async(db_session, email="custom@test.com")

    # Create team
    team = await TeamFactory.create_async(db_session, user_id=user.id)
"""

from tests.factories.user import UserFactory
from tests.factories.team import TeamFactory
from tests.factories.organization import OrganizationFactory
from tests.factories.team_member import TeamMemberFactory
from tests.factories.organization_member import OrganizationMemberFactory

__all__ = [
    "UserFactory",
    "TeamFactory",
    "OrganizationFactory",
    "TeamMemberFactory",
    "OrganizationMemberFactory",
]
