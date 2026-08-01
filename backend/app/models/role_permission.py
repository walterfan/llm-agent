"""RolePermission association model for RBAC system."""

from sqlalchemy import Column, ForeignKey, Integer, Table
from app.db.base import Base


# Association table for many-to-many relationship between roles and permissions
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column(
        "role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    ),
    Column(
        "permission_id",
        Integer,
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)
