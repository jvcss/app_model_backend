"""
Organizations API Endpoints

Provides CRUD operations for organizations (Provider, Client, Guest)
and management of organization members.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.models.organization import Organization
from app.models.provider import Provider
from app.models.client import Client
from app.models.guest import Guest
from app.models.organization_member import OrganizationMember
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationOut,
    OrganizationWithDetails
)
from app.schemas.provider import ProviderCreate, ProviderOut, ProviderUpdate
from app.schemas.client import ClientCreate, ClientOut, ClientUpdate
from app.schemas.guest import GuestCreate, GuestOut, GuestUpdate
from app.schemas.organization_member import (
    OrganizationMemberCreate,
    OrganizationMemberUpdate,
    OrganizationMemberOut,
    OrganizationMemberWithUser
)

router = APIRouter()


# ==================== Organization CRUD ====================

@router.post("/", response_model=OrganizationOut, status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_data: OrganizationCreate,
    type_data: Optional[ProviderCreate | ClientCreate | GuestCreate] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new organization.

    The organization type determines which type-specific data can be provided:
    - provider: services_offered, capabilities, certification_info
    - client: contract_number, billing_info, payment_terms
    - guest: access_expires_at, access_scope
    """
    # Create base organization
    new_org = Organization(
        name=org_data.name,
        organization_type=org_data.organization_type,
        email=org_data.email,
        phone=org_data.phone,
        address=org_data.address
    )
    db.add(new_org)
    await db.flush()  # Get org.id

    # Create type-specific data based on organization_type
    if org_data.organization_type == "provider" and type_data and isinstance(type_data, ProviderCreate):
        provider = Provider(
            organization_id=new_org.id,
            services_offered=type_data.services_offered,
            capabilities=type_data.capabilities,
            certification_info=type_data.certification_info
        )
        db.add(provider)
    elif org_data.organization_type == "client" and type_data and isinstance(type_data, ClientCreate):
        client = Client(
            organization_id=new_org.id,
            contract_number=type_data.contract_number,
            billing_info=type_data.billing_info,
            payment_terms=type_data.payment_terms
        )
        db.add(client)
    elif org_data.organization_type == "guest" and type_data and isinstance(type_data, GuestCreate):
        guest = Guest(
            organization_id=new_org.id,
            access_expires_at=type_data.access_expires_at,
            invited_by=current_user.id,
            access_scope=type_data.access_scope
        )
        db.add(guest)

    # Add creator as admin member
    member = OrganizationMember(
        organization_id=new_org.id,
        user_id=current_user.id,
        role="admin",
        status="active"
    )
    db.add(member)

    await db.commit()
    await db.refresh(new_org)

    return new_org


@router.get("/", response_model=List[OrganizationOut])
async def list_organizations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    organization_type: Optional[str] = Query(None, pattern="^(provider|client|guest)$"),
    archived: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List organizations where the current user is a member.

    Query parameters:
    - skip: Number of records to skip (pagination)
    - limit: Maximum number of records to return
    - organization_type: Filter by type (provider, client, guest)
    - archived: Include archived organizations
    """
    # Build query to get organizations where user is a member
    query = (
        select(Organization)
        .join(OrganizationMember, OrganizationMember.organization_id == Organization.id)
        .filter(
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.status == "active"
        )
    )

    # Apply filters
    if organization_type:
        query = query.filter(Organization.organization_type == organization_type)

    if not archived:
        query = query.filter(Organization.archived == False)

    # Apply pagination
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    organizations = result.scalars().all()

    return organizations


@router.get("/{organization_id}", response_model=OrganizationWithDetails)
async def get_organization(
    organization_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific organization by ID.

    Returns organization with type-specific details.
    Only accessible to organization members.
    """
    # Check if user is a member
    member_check = await db.execute(
        select(OrganizationMember).filter(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.status == "active"
        )
    )
    if not member_check.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization"
        )

    # Get organization with type-specific data
    result = await db.execute(
        select(Organization)
        .options(
            selectinload(Organization.provider),
            selectinload(Organization.client),
            selectinload(Organization.guest)
        )
        .filter(Organization.id == organization_id)
    )
    organization = result.scalar_one_or_none()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # Build response with type-specific details
    response = OrganizationWithDetails.model_validate(organization)

    # Add type-specific details
    if organization.organization_type == "provider" and organization.provider:
        response.type_details = ProviderOut.model_validate(organization.provider).model_dump()
    elif organization.organization_type == "client" and organization.client:
        response.type_details = ClientOut.model_validate(organization.client).model_dump()
    elif organization.organization_type == "guest" and organization.guest:
        response.type_details = GuestOut.model_validate(organization.guest).model_dump()

    return response


@router.patch("/{organization_id}", response_model=OrganizationOut)
async def update_organization(
    organization_id: int,
    org_update: OrganizationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update an organization.

    Only admin members can update the organization.
    """
    # Check if user is an admin member
    member_check = await db.execute(
        select(OrganizationMember).filter(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.role == "admin",
            OrganizationMember.status == "active"
        )
    )
    if not member_check.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization admins can update the organization"
        )

    # Get organization
    result = await db.execute(
        select(Organization).filter(Organization.id == organization_id)
    )
    organization = result.scalar_one_or_none()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # Update fields
    update_data = org_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(organization, field, value)

    await db.commit()
    await db.refresh(organization)

    return organization


@router.delete("/{organization_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    organization_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete (archive) an organization.

    Only admin members can delete the organization.
    This performs a soft delete (sets archived=True).
    """
    # Check if user is an admin member
    member_check = await db.execute(
        select(OrganizationMember).filter(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.role == "admin",
            OrganizationMember.status == "active"
        )
    )
    if not member_check.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization admins can delete the organization"
        )

    # Get organization
    result = await db.execute(
        select(Organization).filter(Organization.id == organization_id)
    )
    organization = result.scalar_one_or_none()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # Soft delete
    from datetime import datetime, timezone
    organization.archived = True
    organization.archived_at = datetime.now(timezone.utc)

    await db.commit()


# ==================== Organization Members ====================

@router.post("/{organization_id}/members", response_model=OrganizationMemberOut, status_code=status.HTTP_201_CREATED)
async def add_organization_member(
    organization_id: int,
    member_data: OrganizationMemberCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a user as a member to the organization.

    Only admin members can add new members.
    """
    # Check if current user is an admin
    admin_check = await db.execute(
        select(OrganizationMember).filter(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.role == "admin",
            OrganizationMember.status == "active"
        )
    )
    if not admin_check.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization admins can add members"
        )

    # Check if organization exists
    org_result = await db.execute(
        select(Organization).filter(Organization.id == organization_id)
    )
    if not org_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

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
        select(OrganizationMember).filter(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == member_data.user_id
        )
    )
    if existing_member.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this organization"
        )

    # Create new member
    new_member = OrganizationMember(
        organization_id=organization_id,
        user_id=member_data.user_id,
        role=member_data.role,
        status="active"
    )
    db.add(new_member)
    await db.commit()
    await db.refresh(new_member)

    return new_member


@router.get("/{organization_id}/members", response_model=List[OrganizationMemberWithUser])
async def list_organization_members(
    organization_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all members of an organization.

    Only organization members can view the member list.
    """
    # Check if user is a member
    member_check = await db.execute(
        select(OrganizationMember).filter(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.status == "active"
        )
    )
    if not member_check.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization"
        )

    # Get all members with user info
    result = await db.execute(
        select(OrganizationMember, User)
        .join(User, User.id == OrganizationMember.user_id)
        .filter(OrganizationMember.organization_id == organization_id)
        .offset(skip)
        .limit(limit)
    )
    members = result.all()

    # Build response with user details
    response = []
    for member, user in members:
        member_data = OrganizationMemberWithUser.model_validate(member)
        member_data.user_name = user.name
        member_data.user_email = user.email
        response.append(member_data)

    return response


@router.patch("/{organization_id}/members/{user_id}", response_model=OrganizationMemberOut)
async def update_organization_member(
    organization_id: int,
    user_id: int,
    member_update: OrganizationMemberUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update an organization member's role or status.

    Only admin members can update other members.
    """
    # Check if current user is an admin
    admin_check = await db.execute(
        select(OrganizationMember).filter(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.role == "admin",
            OrganizationMember.status == "active"
        )
    )
    if not admin_check.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization admins can update members"
        )

    # Get member to update
    result = await db.execute(
        select(OrganizationMember).filter(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id
        )
    )
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )

    # Update fields
    update_data = member_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(member, field, value)

    await db.commit()
    await db.refresh(member)

    return member


@router.delete("/{organization_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_organization_member(
    organization_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove a member from the organization.

    Only admin members can remove other members.
    Cannot remove the last admin.
    """
    # Check if current user is an admin
    admin_check = await db.execute(
        select(OrganizationMember).filter(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.role == "admin",
            OrganizationMember.status == "active"
        )
    )
    if not admin_check.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization admins can remove members"
        )

    # Get member to remove
    result = await db.execute(
        select(OrganizationMember).filter(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id
        )
    )
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )

    # If removing an admin, check if there are other admins
    if member.role == "admin":
        admin_count = await db.execute(
            select(OrganizationMember).filter(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.role == "admin",
                OrganizationMember.status == "active"
            )
        )
        if len(admin_count.scalars().all()) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the last admin from the organization"
            )

    # Remove member
    await db.delete(member)
    await db.commit()
