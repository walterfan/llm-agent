"""Permission checking service for authorization."""

import logging
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.role import Role
from app.models.permission import Permission

logger = logging.getLogger(__name__)


class PermissionChecker:
    """Service for checking user permissions."""

    # Map UserRole ENUM to Role names in database
    ROLE_NAME_MAPPING = {
        UserRole.SUPER_ADMIN: "Super Administrator",
        UserRole.ADMIN: "Administrator",
        UserRole.USER: "Regular User",
        UserRole.GUEST: "Guest",
    }

    @staticmethod
    def get_user_permissions(db: Session, user: User) -> set[str]:
        """
        Get all permission names for a user based on their role.

        Returns a set of permission names (e.g., {"user.read", "user.create"})
        """
        # Map user's ENUM role to database role name
        role_name = PermissionChecker.ROLE_NAME_MAPPING.get(user.role)

        if not role_name:
            logger.warning(f"Unknown role for user {user.email}: {user.role}")
            return set()

        # Query the database role with permissions
        role = db.query(Role).filter(Role.name == role_name).first()

        if not role:
            logger.warning(
                f"Role '{role_name}' not found in database for user {user.email}"
            )
            return set()

        # Extract permission names
        permission_names = {perm.name for perm in role.permissions}

        logger.debug(
            f"User {user.email} has {len(permission_names)} permissions from role '{role_name}'"
        )

        return permission_names

    @staticmethod
    def has_permission(db: Session, user: User, required_permission: str) -> bool:
        """
        Check if user has a specific permission.

        Args:
            db: Database session
            user: User to check
            required_permission: Permission name (e.g., "user.create")

        Returns:
            True if user has the permission, False otherwise
        """
        user_permissions = PermissionChecker.get_user_permissions(db, user)
        has_perm = required_permission in user_permissions

        if has_perm:
            logger.debug(f"✅ User {user.email} has permission '{required_permission}'")
        else:
            logger.warning(
                f"❌ User {user.email} lacks permission '{required_permission}'"
            )

        return has_perm

    @staticmethod
    def has_any_permission(
        db: Session, user: User, required_permissions: list[str]
    ) -> bool:
        """
        Check if user has ANY of the specified permissions.

        Args:
            db: Database session
            user: User to check
            required_permissions: List of permission names

        Returns:
            True if user has at least one permission, False otherwise
        """
        user_permissions = PermissionChecker.get_user_permissions(db, user)
        has_any = any(perm in user_permissions for perm in required_permissions)

        if has_any:
            logger.debug(
                f"✅ User {user.email} has at least one of: {required_permissions}"
            )
        else:
            logger.warning(f"❌ User {user.email} lacks all of: {required_permissions}")

        return has_any

    @staticmethod
    def has_all_permissions(
        db: Session, user: User, required_permissions: list[str]
    ) -> bool:
        """
        Check if user has ALL of the specified permissions.

        Args:
            db: Database session
            user: User to check
            required_permissions: List of permission names

        Returns:
            True if user has all permissions, False otherwise
        """
        user_permissions = PermissionChecker.get_user_permissions(db, user)
        has_all = all(perm in user_permissions for perm in required_permissions)

        if has_all:
            logger.debug(f"✅ User {user.email} has all of: {required_permissions}")
        else:
            logger.warning(
                f"❌ User {user.email} lacks some of: {required_permissions}"
            )

        return has_all
