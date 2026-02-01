from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.base import Base


class Permission(Base):
    """
    Registry of available permissions in the system.

    Each permission is a resource-action pair (e.g., 'team:delete', 'service:create').
    Permissions are then assigned to roles via RolePermission.
    """
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    resource = Column(String(50), nullable=False, index=True)  # 'team', 'project', 'service', etc.
    action = Column(String(50), nullable=False, index=True)  # 'read', 'create', 'update', 'delete', etc.
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    role_permissions = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        UniqueConstraint('resource', 'action', name='uq_resource_action'),
    )

    def __repr__(self):
        return f"<Permission(id={self.id}, resource='{self.resource}', action='{self.action}')>"


class RolePermission(Base):
    """
    Association table linking Roles to Permissions.

    Defines which permissions each role has.
    This is primarily for future database-driven permission management.
    Currently, permissions are defined in code (app/core/permissions.py).
    """
    __tablename__ = "role_permissions"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String(20), nullable=False, index=True)  # 'admin', 'member', 'viewer'
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False)
    granted = Column(Boolean, default=True)  # Allow for explicit deny if needed
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    permission = relationship("Permission", back_populates="role_permissions")

    # Constraints
    __table_args__ = (
        UniqueConstraint('role', 'permission_id', name='uq_role_permission'),
    )

    def __repr__(self):
        return f"<RolePermission(role='{self.role}', permission_id={self.permission_id}, granted={self.granted})>"
