"""
Organization factory for test data generation.

Handles polymorphic organization types (provider, client, guest).
"""

import factory
from factory import fuzzy
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.provider import Provider
from app.models.client import Client
from app.models.guest import Guest


class OrganizationFactory(factory.Factory):
    """
    Factory for Organization model.

    Automatically creates type-specific data (Provider, Client, or Guest).
    """

    class Meta:
        model = Organization

    id = factory.Sequence(lambda n: n + 1)
    name = factory.Faker("company")
    organization_type = fuzzy.FuzzyChoice(["provider", "client", "guest"])
    email = factory.Faker("company_email")
    phone = factory.Faker("phone_number")
    address = factory.Faker("address")
    archived = False
    archived_at = None

    @classmethod
    async def create_async(
        cls,
        db_session: AsyncSession,
        **kwargs
    ) -> Organization:
        """
        Create organization in database asynchronously.

        Automatically creates type-specific data based on organization_type.

        Args:
            db_session: AsyncSession instance
            **kwargs: Override factory attributes

        Returns:
            Organization instance (with provider/client/guest relationship)

        Usage:
            # Provider
            org = await OrganizationFactory.create_async(
                db_session,
                organization_type="provider"
            )

            # Client with custom data
            org = await OrganizationFactory.create_async(
                db_session,
                organization_type="client",
                name="ACME Corp"
            )
        """
        instance = cls.build(**kwargs)
        db_session.add(instance)
        await db_session.flush()

        # Create type-specific data
        if instance.organization_type == "provider":
            provider = Provider(
                organization_id=instance.id,
                services_offered=["Development", "Consulting", "Support"],
                capabilities={
                    "languages": ["Python", "JavaScript", "TypeScript"],
                    "frameworks": ["FastAPI", "React", "Next.js"],
                    "industries": ["FinTech", "HealthTech", "E-commerce"]
                },
                certification_info="ISO 9001:2015, SOC 2 Type II",
                verified=True
            )
            db_session.add(provider)

        elif instance.organization_type == "client":
            client = Client(
                organization_id=instance.id,
                contract_number=f"CONTRACT-{instance.id:06d}",
                billing_info={
                    "payment_method": "wire_transfer",
                    "billing_cycle": "monthly",
                    "currency": "USD"
                },
                payment_terms="Net 30"
            )
            db_session.add(client)

        elif instance.organization_type == "guest":
            guest = Guest(
                organization_id=instance.id,
                access_expires_at=datetime.now(timezone.utc) + timedelta(days=30),
                invited_by=None,  # Can be set manually
                access_scope={
                    "resources": ["projects", "documents"],
                    "permissions": ["read"]
                }
            )
            db_session.add(guest)

        await db_session.flush()
        return instance


class ProviderFactory(factory.Factory):
    """
    Convenience factory for Provider organizations.
    """

    class Meta:
        model = Organization

    id = factory.Sequence(lambda n: n + 1)
    name = factory.Faker("company")
    organization_type = "provider"
    email = factory.Faker("company_email")

    @classmethod
    async def create_async(cls, db_session: AsyncSession, **kwargs) -> Organization:
        kwargs["organization_type"] = "provider"
        return await OrganizationFactory.create_async(db_session, **kwargs)


class ClientFactory(factory.Factory):
    """
    Convenience factory for Client organizations.
    """

    class Meta:
        model = Organization

    id = factory.Sequence(lambda n: n + 1)
    name = factory.Faker("company")
    organization_type = "client"
    email = factory.Faker("company_email")

    @classmethod
    async def create_async(cls, db_session: AsyncSession, **kwargs) -> Organization:
        kwargs["organization_type"] = "client"
        return await OrganizationFactory.create_async(db_session, **kwargs)


class GuestFactory(factory.Factory):
    """
    Convenience factory for Guest organizations.
    """

    class Meta:
        model = Organization

    id = factory.Sequence(lambda n: n + 1)
    name = factory.Faker("company")
    organization_type = "guest"
    email = factory.Faker("company_email")

    @classmethod
    async def create_async(cls, db_session: AsyncSession, **kwargs) -> Organization:
        kwargs["organization_type"] = "guest"
        return await OrganizationFactory.create_async(db_session, **kwargs)
