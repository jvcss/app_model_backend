"""
Permission system for role-based access control (RBAC).

Defines roles, resources, actions, and permission matrices.
Permissions are role-based with additional permissions for organization types.
"""

from enum import Enum
from typing import Dict, Set, Tuple, Optional


class TeamRole(str, Enum):
    """Roles for team members (Users or Organizations)"""
    ADMIN = "admin"      # Full control of the team
    MEMBER = "member"    # Standard access
    VIEWER = "viewer"    # Read-only access


class OrganizationType(str, Enum):
    """Types of organizations"""
    PROVIDER = "provider"  # Service providers
    CLIENT = "client"      # Service consumers
    GUEST = "guest"        # Temporary/limited access


class Resource(str, Enum):
    """Resources that can be accessed"""
    TEAM = "team"
    TEAM_MEMBER = "team_member"
    PROJECT = "project"
    SERVICE = "service"
    INVOICE = "invoice"
    REPORT = "report"
    ORGANIZATION = "organization"


class Action(str, Enum):
    """Actions that can be performed on resources"""
    READ = "read"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    INVITE = "invite"
    REMOVE = "remove"
    MANAGE = "manage"


# Permission matrix for team roles
ROLE_PERMISSIONS: Dict[TeamRole, Set[Tuple[Resource, Action]]] = {
    TeamRole.ADMIN: {
        # Full team management
        (Resource.TEAM, Action.READ),
        (Resource.TEAM, Action.UPDATE),
        (Resource.TEAM, Action.DELETE),
        # Member management
        (Resource.TEAM_MEMBER, Action.READ),
        (Resource.TEAM_MEMBER, Action.INVITE),
        (Resource.TEAM_MEMBER, Action.REMOVE),
        (Resource.TEAM_MEMBER, Action.MANAGE),
        # Project management
        (Resource.PROJECT, Action.READ),
        (Resource.PROJECT, Action.CREATE),
        (Resource.PROJECT, Action.UPDATE),
        (Resource.PROJECT, Action.DELETE),
        # Service management
        (Resource.SERVICE, Action.READ),
        (Resource.SERVICE, Action.CREATE),
        (Resource.SERVICE, Action.UPDATE),
        (Resource.SERVICE, Action.DELETE),
        # Financial
        (Resource.INVOICE, Action.READ),
        (Resource.INVOICE, Action.CREATE),
        # Reporting
        (Resource.REPORT, Action.READ),
        # Organization access
        (Resource.ORGANIZATION, Action.READ),
    },
    TeamRole.MEMBER: {
        # Team info
        (Resource.TEAM, Action.READ),
        (Resource.TEAM_MEMBER, Action.READ),
        # Project collaboration
        (Resource.PROJECT, Action.READ),
        (Resource.PROJECT, Action.UPDATE),
        # Service usage
        (Resource.SERVICE, Action.READ),
        (Resource.SERVICE, Action.UPDATE),
        # View financials
        (Resource.INVOICE, Action.READ),
        # View reports
        (Resource.REPORT, Action.READ),
    },
    TeamRole.VIEWER: {
        # Read-only access
        (Resource.TEAM, Action.READ),
        (Resource.TEAM_MEMBER, Action.READ),
        (Resource.PROJECT, Action.READ),
        (Resource.SERVICE, Action.READ),
    },
}


# Additional permissions for organization types
ORG_TYPE_PERMISSIONS: Dict[OrganizationType, Set[Tuple[Resource, Action]]] = {
    OrganizationType.PROVIDER: {
        # Providers can manage services
        (Resource.SERVICE, Action.CREATE),
        (Resource.SERVICE, Action.UPDATE),
        (Resource.SERVICE, Action.DELETE),
        (Resource.PROJECT, Action.UPDATE),
        (Resource.PROJECT, Action.CREATE),
    },
    OrganizationType.CLIENT: {
        # Clients can view invoices and create projects
        (Resource.INVOICE, Action.READ),
        (Resource.PROJECT, Action.CREATE),
        (Resource.SERVICE, Action.READ),
    },
    OrganizationType.GUEST: {
        # Guests have minimal access
        (Resource.PROJECT, Action.READ),
        (Resource.SERVICE, Action.READ),
    },
}


def has_permission(
    role: TeamRole,
    resource: Resource,
    action: Action,
    org_type: Optional[OrganizationType] = None
) -> bool:
    """
    Check if a role has permission to perform an action on a resource.

    Args:
        role: Team role (ADMIN, MEMBER, VIEWER)
        resource: Resource being accessed
        action: Action being performed
        org_type: Organization type (if member is an organization)

    Returns:
        True if permission is granted, False otherwise
    """
    # Get base role permissions
    role_perms = ROLE_PERMISSIONS.get(role, set())

    # If organization member, combine with org-specific permissions
    if org_type:
        org_perms = ORG_TYPE_PERMISSIONS.get(org_type, set())
        combined_perms = role_perms | org_perms
        return (resource, action) in combined_perms

    # Regular user member
    return (resource, action) in role_perms


def get_role_permissions(role: TeamRole) -> Set[Tuple[Resource, Action]]:
    """
    Get all permissions for a given role.

    Args:
        role: Team role

    Returns:
        Set of (resource, action) tuples
    """
    return ROLE_PERMISSIONS.get(role, set())


def get_org_type_permissions(org_type: OrganizationType) -> Set[Tuple[Resource, Action]]:
    """
    Get additional permissions for an organization type.

    Args:
        org_type: Organization type

    Returns:
        Set of (resource, action) tuples
    """
    return ORG_TYPE_PERMISSIONS.get(org_type, set())


def can_manage_members(role: TeamRole) -> bool:
    """
    Check if a role can invite/remove team members.

    Args:
        role: Team role

    Returns:
        True if role can manage members
    """
    return has_permission(role, Resource.TEAM_MEMBER, Action.MANAGE)


def can_delete_team(role: TeamRole) -> bool:
    """
    Check if a role can delete the team.

    Args:
        role: Team role

    Returns:
        True if role can delete team
    """
    return has_permission(role, Resource.TEAM, Action.DELETE)
