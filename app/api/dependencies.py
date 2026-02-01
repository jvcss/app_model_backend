from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import SessionAsync, SessionSync
from app.helpers.getters import isDebugMode
from app.models.user import User
from app.core.security import SECRET_KEY, ALGORITHM
from app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/token",
    description="Autenticação via email e senha"
)

async def get_db():
    async with SessionAsync() as session:
        yield session

def get_db_sync():
    db = SessionSync()
    try:
        yield db
    finally:
        db.close()


async def get_current_user(
        token: str = Depends(oauth2_scheme),
                     db: AsyncSession = Depends(get_db),
                     ):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        tv = payload.get("tv")
        if user_id is None or tv is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user or int(tv) != int(user.token_version or 1):
        raise credentials_exception
    return user

async def get_redis():
    redis = await aioredis.from_url(
        settings.CELERY_BROKER_URL_EXTERNAL if isDebugMode() else settings.CELERY_BROKER_URL
    )
    try:
        yield redis
    finally:
        await redis.close()

# ==================== Permission Dependencies ====================

from typing import Dict, Optional
from sqlalchemy import and_
from app.core.permissions import has_permission, Resource, Action, TeamRole, OrganizationType
from app.models.team import Team
from app.models.team_member import TeamMember
from app.models.organization import Organization
from app.models.organization_member import OrganizationMember


async def get_team_member_context(
    team_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict:
    """
    Get team member context for the current user.

    Checks if user is a member of the team either:
    1. Directly (as a User member)
    2. Indirectly (via an Organization they belong to)

    Returns a context dict with user, team, role, and organization info.

    Raises:
        HTTPException 403: If user is not a member of the team
        HTTPException 404: If team not found
    """
    # Check if team exists
    team_result = await db.execute(select(Team).filter(Team.id == team_id))
    team = team_result.scalar_one_or_none()

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )

    # Check if user is the owner (owners have full access)
    if team.user_id == current_user.id:
        return {
            "team_id": team_id,
            "team": team,
            "user": current_user,
            "role": TeamRole.ADMIN,
            "member_type": "owner",
            "organization": None,
            "org_type": None
        }

    # Check for direct membership (User)
    direct_member_result = await db.execute(
        select(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.member_type == "user",
            TeamMember.member_id == current_user.id,
            TeamMember.status == "active"
        )
    )
    direct_member = direct_member_result.scalar_one_or_none()

    if direct_member:
        return {
            "team_id": team_id,
            "team": team,
            "user": current_user,
            "role": TeamRole(direct_member.role),
            "member_type": "user",
            "organization": None,
            "org_type": None
        }

    # Check for membership via Organization
    org_member_result = await db.execute(
        select(TeamMember, Organization)
        .join(Organization, and_(
            TeamMember.member_type == "organization",
            TeamMember.member_id == Organization.id
        ))
        .join(OrganizationMember, OrganizationMember.organization_id == Organization.id)
        .filter(
            TeamMember.team_id == team_id,
            OrganizationMember.user_id == current_user.id,
            TeamMember.status == "active",
            OrganizationMember.status == "active"
        )
    )
    org_membership = org_member_result.first()

    if org_membership:
        team_member, organization = org_membership
        return {
            "team_id": team_id,
            "team": team,
            "user": current_user,
            "role": TeamRole(team_member.role),
            "member_type": "organization",
            "organization": organization,
            "org_type": OrganizationType(organization.organization_type)
        }

    # User is not a member
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You are not a member of this team"
    )


def require_permission(resource: Resource, action: Action):
    """
    Factory to create a dependency that checks if user has permission.

    Usage:
        @router.delete("/{team_id}")
        async def delete_team(
            team_id: int,
            context = Depends(require_permission(Resource.TEAM, Action.DELETE)),
            db: AsyncSession = Depends(get_db)
        ):
            # Only users with TEAM:DELETE permission can access
            ...

    Args:
        resource: Resource being accessed
        action: Action being performed

    Returns:
        Dependency function that validates permissions
    """
    async def permission_checker(
        context: Dict = Depends(get_team_member_context)
    ) -> Dict:
        """
        Check if user has the required permission.

        Args:
            context: Team member context from get_team_member_context

        Returns:
            Context dict if permission granted

        Raises:
            HTTPException 403: If user lacks required permission
        """
        role = context["role"]
        org_type = context.get("org_type")

        if not has_permission(role, resource, action, org_type):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: {action.value} on {resource.value}"
            )

        return context

    return permission_checker


async def require_team_owner(
    team_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Team:
    """
    Dependency to verify that current user is the owner of the team.

    Args:
        team_id: Team ID to check ownership
        current_user: Current authenticated user
        db: Database session

    Returns:
        Team object if user is owner

    Raises:
        HTTPException 404: If team not found
        HTTPException 403: If user is not the owner
    """
    result = await db.execute(
        select(Team).filter(
            Team.id == team_id,
            Team.user_id == current_user.id
        )
    )
    team = result.scalar_one_or_none()

    if not team:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Team not found or you don't have permission"
        )

    return team
