"""
Teams API Endpoints

Provides CRUD operations for teams and team management.
Converted to async for better performance and scalability.
"""

from typing import List, Literal
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.models.team import Team
from app.models.team_member import TeamMember
from app.schemas.team import TeamCreate, TeamUpdate, TeamOut, TeamWithMembers
from app.schemas.team_member import (
    TeamMemberAddUser,
    TeamMemberAddOrganization,
    TeamMemberUpdate,
    TeamMemberOut,
    TeamMemberWithDetails
)
from app.models.organization import Organization
from app.core.permissions import Resource, Action
from app.api.dependencies import require_permission, require_team_owner

router = APIRouter()


# ==================== Team CRUD ====================

@router.get("/", response_model=List[TeamWithMembers])
async def list_teams(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    include_archived: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all teams where the current user is the owner.

    Query parameters:
    - skip: Number of records to skip (pagination)
    - limit: Maximum number of records to return
    - include_archived: Include archived teams
    """
    query = select(Team).filter(Team.user_id == current_user.id)

    if not include_archived:
        query = query.filter(Team.archived == False)

    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    teams = result.scalars().all()

    # Get member count for each team
    response = []
    for team in teams:
        team_data = TeamWithMembers.model_validate(team)

        # Count members
        member_count_query = select(func.count(TeamMember.id)).filter(
            TeamMember.team_id == team.id,
            TeamMember.status == "active"
        )
        member_count_result = await db.execute(member_count_query)
        team_data.member_count = member_count_result.scalar()

        response.append(team_data)

    return response


@router.post("/", response_model=TeamOut, status_code=status.HTTP_201_CREATED)
async def create_team(
    team_data: TeamCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new team.

    The creator becomes the owner of the team.
    A TeamMember record with 'admin' role will be created automatically in the future.
    """
    new_team = Team(
        name=team_data.name,
        description=team_data.description,
        user_id=current_user.id,
        personal_team=team_data.personal_team
    )
    db.add(new_team)
    await db.commit()
    await db.refresh(new_team)

    return new_team


@router.get("/{team_id}", response_model=TeamOut)
async def get_team(
    team_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific team by ID.

    Only the team owner can access this endpoint.
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found or you don't have permission to access it"
        )

    return team


@router.patch("/{team_id}", response_model=TeamOut)
async def update_team(
    team_id: int,
    team_update: TeamUpdate,
    context = Depends(require_permission(Resource.TEAM, Action.UPDATE)),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a team.

    Requires TEAM:UPDATE permission (Admin or Member role).
    """
    team = context["team"]

    # Update fields
    update_data = team_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(team, field, value)

    await db.commit()
    await db.refresh(team)

    return team


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    team_id: int,
    context = Depends(require_permission(Resource.TEAM, Action.DELETE)),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete (archive) a team.

    Requires TEAM:DELETE permission (Admin role).
    This performs a soft delete (sets archived=True).
    Personal teams cannot be deleted.
    """
    team = context["team"]

    if team.personal_team:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete personal teams"
        )

    # Soft delete
    team.archived = True
    team.archived_at = datetime.now(timezone.utc)

    await db.commit()


# ==================== Team Member Management ====================

@router.get("/{team_id}/members", response_model=List[TeamMemberWithDetails])
async def list_team_members(
    team_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all members of a team (Users and Organizations).

    Only team owner or members can view the member list.
    """
    # Check if user is owner or member
    owner_check = await db.execute(
        select(Team).filter(Team.id == team_id, Team.user_id == current_user.id)
    )
    is_owner = owner_check.scalar_one_or_none() is not None

    if not is_owner:
        # Check if user is a member
        member_check = await db.execute(
            select(TeamMember).filter(
                TeamMember.team_id == team_id,
                TeamMember.member_type == "user",
                TeamMember.member_id == current_user.id,
                TeamMember.status == "active"
            )
        )
        if not member_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view team members"
            )

    # Get all team members
    result = await db.execute(
        select(TeamMember)
        .filter(TeamMember.team_id == team_id)
        .offset(skip)
        .limit(limit)
    )
    members = result.scalars().all()

    # Build response with details
    response = []
    for member in members:
        member_data = TeamMemberWithDetails.model_validate(member)

        if member.member_type == "user":
            # Get user details
            user_result = await db.execute(
                select(User).filter(User.id == member.member_id)
            )
            user = user_result.scalar_one_or_none()
            if user:
                member_data.user_name = user.name
                member_data.user_email = user.email
        elif member.member_type == "organization":
            # Get organization details
            org_result = await db.execute(
                select(Organization).filter(Organization.id == member.member_id)
            )
            org = org_result.scalar_one_or_none()
            if org:
                member_data.organization_name = org.name
                member_data.organization_type = org.organization_type

        response.append(member_data)

    return response


@router.post("/{team_id}/members/users", response_model=TeamMemberOut, status_code=status.HTTP_201_CREATED)
async def add_user_to_team(
    team_id: int,
    member_data: TeamMemberAddUser,
    context = Depends(require_permission(Resource.TEAM_MEMBER, Action.INVITE)),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a User as a member to the team.

    Requires TEAM_MEMBER:INVITE permission (Admin role).
    """
    current_user = context["user"]

    # Check if user exists
    user_result = await db.execute(
        select(User).filter(User.id == member_data.user_id)
    )
    if not user_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if user is already a member
    existing_member = await db.execute(
        select(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.member_type == "user",
            TeamMember.member_id == member_data.user_id
        )
    )
    if existing_member.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this team"
        )

    # Create new member
    new_member = TeamMember(
        team_id=team_id,
        member_type="user",
        member_id=member_data.user_id,
        role=member_data.role,
        status="active",
        invited_by=current_user.id,
        joined_at=datetime.now(timezone.utc)
    )
    db.add(new_member)
    await db.commit()
    await db.refresh(new_member)

    return new_member


@router.post("/{team_id}/members/organizations", response_model=TeamMemberOut, status_code=status.HTTP_201_CREATED)
async def add_organization_to_team(
    team_id: int,
    member_data: TeamMemberAddOrganization,
    context = Depends(require_permission(Resource.TEAM_MEMBER, Action.INVITE)),
    db: AsyncSession = Depends(get_db)
):
    """
    Add an Organization as a member to the team.

    Requires TEAM_MEMBER:INVITE permission (Admin role).
    """
    current_user = context["user"]

    # Check if organization exists
    org_result = await db.execute(
        select(Organization).filter(Organization.id == member_data.organization_id)
    )
    if not org_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # Check if organization is already a member
    existing_member = await db.execute(
        select(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.member_type == "organization",
            TeamMember.member_id == member_data.organization_id
        )
    )
    if existing_member.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization is already a member of this team"
        )

    # Create new organization member
    new_member = TeamMember(
        team_id=team_id,
        member_type="organization",
        member_id=member_data.organization_id,
        role=member_data.role,
        status="active",
        invited_by=current_user.id,
        joined_at=datetime.now(timezone.utc)
    )
    db.add(new_member)
    await db.commit()
    await db.refresh(new_member)

    return new_member


@router.patch("/{team_id}/members/{member_type}/{member_id}", response_model=TeamMemberOut)
async def update_team_member(
    team_id: int,
    member_type: Literal["user", "organization"],
    member_id: int,
    member_update: TeamMemberUpdate,
    context = Depends(require_permission(Resource.TEAM_MEMBER, Action.MANAGE)),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a team member's role or status.

    Requires TEAM_MEMBER:MANAGE permission (Admin role).
    """

    # Get member to update
    result = await db.execute(
        select(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.member_type == member_type,
            TeamMember.member_id == member_id
        )
    )
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team member not found"
        )

    # Update fields
    update_data = member_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(member, field, value)

    await db.commit()
    await db.refresh(member)

    return member


@router.delete("/{team_id}/members/{member_type}/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_team_member(
    team_id: int,
    member_type: Literal["user", "organization"],
    member_id: int,
    context = Depends(require_permission(Resource.TEAM_MEMBER, Action.REMOVE)),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove a member from the team.

    Requires TEAM_MEMBER:REMOVE permission (Admin role).
    """

    # Get member to remove
    result = await db.execute(
        select(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.member_type == member_type,
            TeamMember.member_id == member_id
        )
    )
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team member not found"
        )

    # Remove member
    await db.delete(member)
    await db.commit()
