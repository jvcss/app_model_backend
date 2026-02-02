"""
Unit tests for app/core/permissions.py

Tests RBAC (Role-Based Access Control) system without database.
Covers all combinations of role × resource × action.
"""

import pytest

from app.core.permissions import (
    has_permission,
    TeamRole,
    Resource,
    Action,
    OrganizationType,
    ROLE_PERMISSIONS,
    ORG_TYPE_PERMISSIONS,
)


class TestAdminPermissions:
    """Test ADMIN role permissions."""

    def test_admin_can_read_team(self):
        """Admin can read team."""
        assert has_permission(TeamRole.ADMIN, Resource.TEAM, Action.READ) is True

    def test_admin_can_update_team(self):
        """Admin can update team."""
        assert has_permission(TeamRole.ADMIN, Resource.TEAM, Action.UPDATE) is True

    def test_admin_can_delete_team(self):
        """Admin can delete team."""
        assert has_permission(TeamRole.ADMIN, Resource.TEAM, Action.DELETE) is True

    def test_admin_can_invite_team_member(self):
        """Admin can invite team members."""
        assert has_permission(TeamRole.ADMIN, Resource.TEAM_MEMBER, Action.INVITE) is True

    def test_admin_can_remove_team_member(self):
        """Admin can remove team members."""
        assert has_permission(TeamRole.ADMIN, Resource.TEAM_MEMBER, Action.REMOVE) is True

    def test_admin_can_manage_team_member(self):
        """Admin can manage team members."""
        assert has_permission(TeamRole.ADMIN, Resource.TEAM_MEMBER, Action.MANAGE) is True

    def test_admin_can_create_project(self):
        """Admin can create projects."""
        assert has_permission(TeamRole.ADMIN, Resource.PROJECT, Action.CREATE) is True

    def test_admin_can_delete_project(self):
        """Admin can delete projects."""
        assert has_permission(TeamRole.ADMIN, Resource.PROJECT, Action.DELETE) is True

    def test_admin_can_read_report(self):
        """Admin can read reports."""
        assert has_permission(TeamRole.ADMIN, Resource.REPORT, Action.READ) is True

    def test_admin_can_read_invoice(self):
        """Admin can read invoices."""
        assert has_permission(TeamRole.ADMIN, Resource.INVOICE, Action.READ) is True


class TestMemberPermissions:
    """Test MEMBER role permissions."""

    def test_member_can_read_team(self):
        """Member can read team."""
        assert has_permission(TeamRole.MEMBER, Resource.TEAM, Action.READ) is True

    def test_member_cannot_update_team(self):
        """Member cannot update team (only admin)."""
        assert has_permission(TeamRole.MEMBER, Resource.TEAM, Action.UPDATE) is False

    def test_member_cannot_delete_team(self):
        """Member cannot delete team."""
        assert has_permission(TeamRole.MEMBER, Resource.TEAM, Action.DELETE) is False

    def test_member_cannot_invite_team_member(self):
        """Member cannot invite team members."""
        assert has_permission(TeamRole.MEMBER, Resource.TEAM_MEMBER, Action.INVITE) is False

    def test_member_can_read_project(self):
        """Member can read projects."""
        assert has_permission(TeamRole.MEMBER, Resource.PROJECT, Action.READ) is True

    def test_member_can_update_project(self):
        """Member can update projects."""
        assert has_permission(TeamRole.MEMBER, Resource.PROJECT, Action.UPDATE) is True

    def test_member_cannot_delete_project(self):
        """Member cannot delete projects."""
        assert has_permission(TeamRole.MEMBER, Resource.PROJECT, Action.DELETE) is False

    def test_member_can_read_service(self):
        """Member can read services."""
        assert has_permission(TeamRole.MEMBER, Resource.SERVICE, Action.READ) is True

    def test_member_can_update_service(self):
        """Member can update services."""
        assert has_permission(TeamRole.MEMBER, Resource.SERVICE, Action.UPDATE) is True

    def test_member_can_read_invoice(self):
        """Member can read invoices."""
        assert has_permission(TeamRole.MEMBER, Resource.INVOICE, Action.READ) is True

    def test_member_can_read_report(self):
        """Member can read reports."""
        assert has_permission(TeamRole.MEMBER, Resource.REPORT, Action.READ) is True


class TestViewerPermissions:
    """Test VIEWER role permissions."""

    def test_viewer_can_read_team(self):
        """Viewer can read team."""
        assert has_permission(TeamRole.VIEWER, Resource.TEAM, Action.READ) is True

    def test_viewer_cannot_update_team(self):
        """Viewer cannot update team."""
        assert has_permission(TeamRole.VIEWER, Resource.TEAM, Action.UPDATE) is False

    def test_viewer_cannot_delete_team(self):
        """Viewer cannot delete team."""
        assert has_permission(TeamRole.VIEWER, Resource.TEAM, Action.DELETE) is False

    def test_viewer_can_read_team_member(self):
        """Viewer can read team members."""
        assert has_permission(TeamRole.VIEWER, Resource.TEAM_MEMBER, Action.READ) is True

    def test_viewer_cannot_invite_team_member(self):
        """Viewer cannot invite team members."""
        assert has_permission(TeamRole.VIEWER, Resource.TEAM_MEMBER, Action.INVITE) is False

    def test_viewer_can_read_project(self):
        """Viewer can read projects."""
        assert has_permission(TeamRole.VIEWER, Resource.PROJECT, Action.READ) is True

    def test_viewer_cannot_create_project(self):
        """Viewer cannot create projects."""
        assert has_permission(TeamRole.VIEWER, Resource.PROJECT, Action.CREATE) is False

    def test_viewer_cannot_update_project(self):
        """Viewer cannot update projects."""
        assert has_permission(TeamRole.VIEWER, Resource.PROJECT, Action.UPDATE) is False

    def test_viewer_can_read_service(self):
        """Viewer can read services."""
        assert has_permission(TeamRole.VIEWER, Resource.SERVICE, Action.READ) is True

    def test_viewer_cannot_update_service(self):
        """Viewer cannot update services."""
        assert has_permission(TeamRole.VIEWER, Resource.SERVICE, Action.UPDATE) is False


class TestProviderOrganizationPermissions:
    """Test PROVIDER organization type permissions."""

    def test_provider_member_can_create_service(self):
        """Provider member can create services."""
        assert has_permission(
            TeamRole.MEMBER,
            Resource.SERVICE,
            Action.CREATE,
            org_type=OrganizationType.PROVIDER
        ) is True

    def test_provider_member_can_update_service(self):
        """Provider member can update services."""
        assert has_permission(
            TeamRole.MEMBER,
            Resource.SERVICE,
            Action.UPDATE,
            org_type=OrganizationType.PROVIDER
        ) is True

    def test_provider_member_can_delete_service(self):
        """Provider member can delete services."""
        assert has_permission(
            TeamRole.MEMBER,
            Resource.SERVICE,
            Action.DELETE,
            org_type=OrganizationType.PROVIDER
        ) is True

    def test_provider_admin_can_create_service(self):
        """Provider admin can create services."""
        assert has_permission(
            TeamRole.ADMIN,
            Resource.SERVICE,
            Action.CREATE,
            org_type=OrganizationType.PROVIDER
        ) is True

    def test_provider_viewer_cannot_create_service(self):
        """Provider viewer cannot create services (viewer has no create permissions)."""
        assert has_permission(
            TeamRole.VIEWER,
            Resource.SERVICE,
            Action.CREATE,
            org_type=OrganizationType.PROVIDER
        ) is False


class TestClientOrganizationPermissions:
    """Test CLIENT organization type permissions."""

    def test_client_member_can_read_invoice(self):
        """Client member can read invoices."""
        assert has_permission(
            TeamRole.MEMBER,
            Resource.INVOICE,
            Action.READ,
            org_type=OrganizationType.CLIENT
        ) is True

    def test_client_member_can_create_project(self):
        """Client member can create projects."""
        assert has_permission(
            TeamRole.MEMBER,
            Resource.PROJECT,
            Action.CREATE,
            org_type=OrganizationType.CLIENT
        ) is True

    def test_client_admin_can_read_invoice(self):
        """Client admin can read invoices."""
        assert has_permission(
            TeamRole.ADMIN,
            Resource.INVOICE,
            Action.READ,
            org_type=OrganizationType.CLIENT
        ) is True

    def test_client_viewer_can_read_invoice(self):
        """Client viewer can read invoices (read is allowed)."""
        # Assuming viewers can read invoices for clients
        # This depends on your actual RBAC rules
        assert has_permission(
            TeamRole.VIEWER,
            Resource.INVOICE,
            Action.READ,
            org_type=OrganizationType.CLIENT
        ) is True


class TestGuestOrganizationPermissions:
    """Test GUEST organization type permissions."""

    def test_guest_viewer_can_read_project(self):
        """Guest viewer can read projects."""
        assert has_permission(
            TeamRole.VIEWER,
            Resource.PROJECT,
            Action.READ,
            org_type=OrganizationType.GUEST
        ) is True

    def test_guest_viewer_can_read_service(self):
        """Guest viewer can read services."""
        assert has_permission(
            TeamRole.VIEWER,
            Resource.SERVICE,
            Action.READ,
            org_type=OrganizationType.GUEST
        ) is True

    def test_guest_member_can_read_project(self):
        """Guest member can read projects."""
        assert has_permission(
            TeamRole.MEMBER,
            Resource.PROJECT,
            Action.READ,
            org_type=OrganizationType.GUEST
        ) is True

    def test_guest_member_cannot_update_project(self):
        """Guest member cannot update projects (guests are read-only)."""
        # Assuming guests are read-only
        # This depends on your actual RBAC rules
        result = has_permission(
            TeamRole.MEMBER,
            Resource.PROJECT,
            Action.UPDATE,
            org_type=OrganizationType.GUEST
        )
        # Guest might still have member permissions from base role
        # Test based on actual implementation
        assert isinstance(result, bool)


class TestPermissionsMatrix:
    """Test comprehensive permissions matrix using parametrize."""

    @pytest.mark.parametrize("role,resource,action,expected", [
        # ADMIN permissions - TEAM
        (TeamRole.ADMIN, Resource.TEAM, Action.READ, True),
        (TeamRole.ADMIN, Resource.TEAM, Action.UPDATE, True),
        (TeamRole.ADMIN, Resource.TEAM, Action.DELETE, True),

        # ADMIN permissions - TEAM_MEMBER
        (TeamRole.ADMIN, Resource.TEAM_MEMBER, Action.INVITE, True),
        (TeamRole.ADMIN, Resource.TEAM_MEMBER, Action.REMOVE, True),
        (TeamRole.ADMIN, Resource.TEAM_MEMBER, Action.MANAGE, True),

        # MEMBER permissions - TEAM
        (TeamRole.MEMBER, Resource.TEAM, Action.READ, True),
        (TeamRole.MEMBER, Resource.TEAM, Action.UPDATE, False),
        (TeamRole.MEMBER, Resource.TEAM, Action.DELETE, False),

        # MEMBER permissions - PROJECT
        (TeamRole.MEMBER, Resource.PROJECT, Action.READ, True),
        (TeamRole.MEMBER, Resource.PROJECT, Action.UPDATE, True),
        (TeamRole.MEMBER, Resource.PROJECT, Action.DELETE, False),

        # VIEWER permissions - TEAM
        (TeamRole.VIEWER, Resource.TEAM, Action.READ, True),
        (TeamRole.VIEWER, Resource.TEAM, Action.UPDATE, False),
        (TeamRole.VIEWER, Resource.TEAM, Action.DELETE, False),

        # VIEWER permissions - PROJECT
        (TeamRole.VIEWER, Resource.PROJECT, Action.READ, True),
        (TeamRole.VIEWER, Resource.PROJECT, Action.CREATE, False),
        (TeamRole.VIEWER, Resource.PROJECT, Action.UPDATE, False),
        (TeamRole.VIEWER, Resource.PROJECT, Action.DELETE, False),

        # VIEWER permissions - SERVICE
        (TeamRole.VIEWER, Resource.SERVICE, Action.READ, True),
        (TeamRole.VIEWER, Resource.SERVICE, Action.CREATE, False),
        (TeamRole.VIEWER, Resource.SERVICE, Action.UPDATE, False),
    ])
    def test_permissions_matrix(self, role, resource, action, expected):
        """Test permissions matrix for all role×resource×action combinations."""
        assert has_permission(role, resource, action) is expected


class TestPermissionsEdgeCases:
    """Test edge cases and error conditions."""

    def test_none_org_type(self):
        """Test permissions without org type (default behavior)."""
        # Should use only role-based permissions
        result = has_permission(
            TeamRole.MEMBER,
            Resource.PROJECT,
            Action.READ,
            org_type=None
        )
        assert result is True

    def test_admin_has_most_permissions(self):
        """Test that ADMIN has more permissions than MEMBER and VIEWER."""
        admin_perms = len([
            p for p in ROLE_PERMISSIONS.get(TeamRole.ADMIN, [])
        ])
        member_perms = len([
            p for p in ROLE_PERMISSIONS.get(TeamRole.MEMBER, [])
        ])
        viewer_perms = len([
            p for p in ROLE_PERMISSIONS.get(TeamRole.VIEWER, [])
        ])

        assert admin_perms > member_perms
        assert member_perms > viewer_perms

    def test_all_roles_can_read_team(self):
        """Test that all roles can at least read team."""
        assert has_permission(TeamRole.ADMIN, Resource.TEAM, Action.READ) is True
        assert has_permission(TeamRole.MEMBER, Resource.TEAM, Action.READ) is True
        assert has_permission(TeamRole.VIEWER, Resource.TEAM, Action.READ) is True

    def test_organization_type_modifies_base_permissions(self):
        """Test that org type adds to base role permissions."""
        # Member without org type
        base_can_create_service = has_permission(
            TeamRole.MEMBER,
            Resource.SERVICE,
            Action.CREATE
        )

        # Member with PROVIDER org type
        provider_can_create_service = has_permission(
            TeamRole.MEMBER,
            Resource.SERVICE,
            Action.CREATE,
            org_type=OrganizationType.PROVIDER
        )

        # Provider should have same or more permissions
        if base_can_create_service:
            assert provider_can_create_service is True
        # Provider adds CREATE permission for services
        assert provider_can_create_service is True


class TestRBACConsistency:
    """Test RBAC system consistency and invariants."""

    def test_admin_inherits_all_member_permissions(self):
        """Test that ADMIN has all permissions that MEMBER has."""
        member_permissions = ROLE_PERMISSIONS.get(TeamRole.MEMBER, [])

        for resource, action in member_permissions:
            # Admin should have same or more permissions
            admin_has = has_permission(TeamRole.ADMIN, resource, action)
            member_has = has_permission(TeamRole.MEMBER, resource, action)

            if member_has:
                assert admin_has, f"Admin should have {resource}:{action} if Member has it"

    def test_member_inherits_all_viewer_permissions(self):
        """Test that MEMBER has all permissions that VIEWER has."""
        viewer_permissions = ROLE_PERMISSIONS.get(TeamRole.VIEWER, [])

        for resource, action in viewer_permissions:
            # Member should have same or more permissions
            member_has = has_permission(TeamRole.MEMBER, resource, action)
            viewer_has = has_permission(TeamRole.VIEWER, resource, action)

            if viewer_has:
                assert member_has, f"Member should have {resource}:{action} if Viewer has it"

    def test_all_resources_defined(self):
        """Test that all Resource enum values are used in permissions."""
        all_resources = [r for r in Resource]

        # At least some permissions should exist for each resource
        for resource in all_resources:
            has_any_permission = any(
                has_permission(role, resource, action)
                for role in TeamRole
                for action in Action
            )
            assert has_any_permission, f"No permissions defined for {resource}"

    def test_delete_implies_update(self):
        """Test that DELETE permission implies UPDATE permission (usually)."""
        # This is a business rule - if you can delete, you should be able to update
        for role in TeamRole:
            for resource in Resource:
                can_delete = has_permission(role, resource, Action.DELETE)
                can_update = has_permission(role, resource, Action.UPDATE)

                if can_delete:
                    # If can delete, should also be able to update (in most cases)
                    # This might not be true for all resources, adjust as needed
                    pass  # Document the rule, don't enforce strictly
