"""RBAC service for managing roles and permissions."""

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import role_permissions
from app.schemas.rbac import (
    PermissionCreate,
    PermissionUpdate,
    RoleCreate,
    RoleUpdate,
)


class PermissionService:
    """Service for permission management."""

    @staticmethod
    def get_permissions(
        db: Session,
        skip: int = 0,
        limit: int = 20,
        resource: str | None = None,
    ) -> tuple[list[Permission], int]:
        """
        Get paginated list of permissions with optional filtering.

        Returns: (permissions, total_count)
        """
        query = db.query(Permission)

        # Apply resource filter
        if resource:
            query = query.filter(Permission.resource == resource)

        # Get total count
        total = query.count()

        # Apply pagination and sorting
        permissions = query.order_by(Permission.name).offset(skip).limit(limit).all()

        return permissions, total

    @staticmethod
    def get_permission_by_id(db: Session, permission_id: int) -> Permission | None:
        """Get permission by ID."""
        return db.query(Permission).filter(Permission.id == permission_id).first()

    @staticmethod
    def get_permission_by_name(db: Session, name: str) -> Permission | None:
        """Get permission by name."""
        return db.query(Permission).filter(Permission.name == name).first()

    @staticmethod
    def create_permission(
        db: Session, permission_create: PermissionCreate
    ) -> Permission:
        """Create a new permission."""
        # Check if permission already exists
        existing = PermissionService.get_permission_by_name(db, permission_create.name)
        if existing:
            raise ValueError(f"Permission '{permission_create.name}' already exists")

        permission = Permission(
            name=permission_create.name,
            resource=permission_create.resource,
            action=permission_create.action,
            description=permission_create.description,
        )
        db.add(permission)
        db.commit()
        db.refresh(permission)
        return permission

    @staticmethod
    def update_permission(
        db: Session,
        permission_id: int,
        permission_update: PermissionUpdate,
    ) -> Permission:
        """Update permission."""
        permission = PermissionService.get_permission_by_id(db, permission_id)
        if not permission:
            raise ValueError("Permission not found")

        # Check name uniqueness if changing name
        if permission_update.name and permission_update.name != permission.name:
            existing = PermissionService.get_permission_by_name(
                db, permission_update.name
            )
            if existing:
                raise ValueError(
                    f"Permission '{permission_update.name}' already exists"
                )
            permission.name = permission_update.name

        if permission_update.resource is not None:
            permission.resource = permission_update.resource
        if permission_update.action is not None:
            permission.action = permission_update.action
        if permission_update.description is not None:
            permission.description = permission_update.description

        db.add(permission)
        db.commit()
        db.refresh(permission)
        return permission

    @staticmethod
    def delete_permission(db: Session, permission_id: int) -> None:
        """Delete permission."""
        permission = PermissionService.get_permission_by_id(db, permission_id)
        if not permission:
            raise ValueError("Permission not found")

        db.delete(permission)
        db.commit()


class RoleService:
    """Service for role management."""

    @staticmethod
    def get_roles(
        db: Session,
        skip: int = 0,
        limit: int = 20,
        search: str | None = None,
    ) -> tuple[list[Role], int]:
        """
        Get paginated list of roles with optional search.

        Returns: (roles, total_count)
        """
        query = db.query(Role)

        # Apply search filter
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(Role.name.ilike(search_pattern))

        # Get total count
        total = query.count()

        # Apply pagination and sorting
        roles = query.order_by(Role.name).offset(skip).limit(limit).all()

        return roles, total

    @staticmethod
    def get_role_by_id(db: Session, role_id: int) -> Role | None:
        """Get role by ID with permissions."""
        return db.query(Role).filter(Role.id == role_id).first()

    @staticmethod
    def get_role_by_name(db: Session, name: str) -> Role | None:
        """Get role by name."""
        return db.query(Role).filter(Role.name == name).first()

    @staticmethod
    def create_role(db: Session, role_create: RoleCreate) -> Role:
        """Create a new role with permissions."""
        # Check if role already exists
        existing = RoleService.get_role_by_name(db, role_create.name)
        if existing:
            raise ValueError(f"Role '{role_create.name}' already exists")

        role = Role(
            name=role_create.name,
            description=role_create.description,
        )

        # Assign permissions
        if role_create.permission_ids:
            permissions = (
                db.query(Permission)
                .filter(Permission.id.in_(role_create.permission_ids))
                .all()
            )
            role.permissions = permissions

        db.add(role)
        db.commit()
        db.refresh(role)
        return role

    @staticmethod
    def update_role(
        db: Session,
        role_id: int,
        role_update: RoleUpdate,
    ) -> Role:
        """Update role."""
        role = RoleService.get_role_by_id(db, role_id)
        if not role:
            raise ValueError("Role not found")

        # Check name uniqueness if changing name
        if role_update.name and role_update.name != role.name:
            existing = RoleService.get_role_by_name(db, role_update.name)
            if existing:
                raise ValueError(f"Role '{role_update.name}' already exists")
            role.name = role_update.name

        if role_update.description is not None:
            role.description = role_update.description

        # Update permissions if provided
        if role_update.permission_ids is not None:
            permissions = (
                db.query(Permission)
                .filter(Permission.id.in_(role_update.permission_ids))
                .all()
            )
            role.permissions = permissions

        db.add(role)
        db.commit()
        db.refresh(role)
        return role

    @staticmethod
    def delete_role(db: Session, role_id: int) -> None:
        """Delete role."""
        role = RoleService.get_role_by_id(db, role_id)
        if not role:
            raise ValueError("Role not found")

        db.delete(role)
        db.commit()

    @staticmethod
    def add_permissions_to_role(
        db: Session,
        role_id: int,
        permission_ids: list[int],
    ) -> Role:
        """Add permissions to a role."""
        role = RoleService.get_role_by_id(db, role_id)
        if not role:
            raise ValueError("Role not found")

        permissions = (
            db.query(Permission).filter(Permission.id.in_(permission_ids)).all()
        )

        # Add only new permissions (avoid duplicates)
        existing_ids = {p.id for p in role.permissions}
        for permission in permissions:
            if permission.id not in existing_ids:
                role.permissions.append(permission)

        db.add(role)
        db.commit()
        db.refresh(role)
        return role

    @staticmethod
    def remove_permissions_from_role(
        db: Session,
        role_id: int,
        permission_ids: list[int],
    ) -> Role:
        """Remove permissions from a role."""
        role = RoleService.get_role_by_id(db, role_id)
        if not role:
            raise ValueError("Role not found")

        # Remove specified permissions
        role.permissions = [p for p in role.permissions if p.id not in permission_ids]

        db.add(role)
        db.commit()
        db.refresh(role)
        return role
