from datetime import timedelta
from typing import Annotated, Optional
import logging

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.base import get_db
from app.models.user import User, UserRole
from app.services.user_service import UserService
from app.services.permission_service import PermissionChecker

logger = logging.getLogger(__name__)

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/signin")


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    token: Annotated[str, Depends(oauth2_scheme)],
) -> User:
    """Dependency to get the current authenticated user from JWT token."""
    import logging

    logger = logging.getLogger(__name__)

    logger.debug("🔐 [AUTH-HEADER] Starting header-based authentication")

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Log token info (first/last 10 chars only for security)
    token_preview = (
        f"{token[:10]}...{token[-10:]}" if len(token) > 20 else "TOKEN_TOO_SHORT"
    )
    logger.debug(f"🔑 [AUTH-HEADER] Token received: {token_preview}")

    # Decode token
    payload = decode_access_token(token)
    if payload is None:
        logger.warning(f"❌ [AUTH-HEADER] Token decode failed for: {token_preview}")
        raise credentials_exception

    logger.debug(f"✅ [AUTH-HEADER] Token decoded successfully. Payload: {payload}")

    user_id: str | None = payload.get("sub")
    if user_id is None:
        logger.warning("❌ [AUTH-HEADER] No 'sub' field in token payload")
        raise credentials_exception

    logger.debug(f"👤 [AUTH-HEADER] User ID from token: {user_id}")

    # Get user from database
    try:
        user = UserService.get_user_by_id(db, int(user_id))
        if user is None:
            logger.warning(
                f"❌ [AUTH-HEADER] User not found in database: user_id={user_id}"
            )
            raise credentials_exception

        logger.debug(
            f"✅ [AUTH-HEADER] User found: {user.email} (id={user.id}, active={user.is_active})"
        )

    except ValueError as e:
        logger.warning(f"❌ [AUTH-HEADER] Invalid user_id format: {user_id} - {e}")
        raise credentials_exception

    if not user.is_active:
        logger.warning(
            f"❌ [AUTH-HEADER] User account is inactive: {user.email} (id={user.id})"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive",
        )

    logger.info(
        f"✅ [AUTH-HEADER] Authentication successful: {user.email} (id={user.id})"
    )
    return user


def get_current_user_from_query(
    db: Annotated[Session, Depends(get_db)],
    token: Optional[str] = Query(None, description="JWT access token"),
) -> User:
    """
    Dependency to get the current authenticated user from query parameter.

    This is used for EventSource/SSE endpoints where headers cannot be set.
    For security, this should only be used for streaming endpoints.
    """
    import logging

    logger = logging.getLogger(__name__)

    logger.debug("🔐 [AUTH-QUERY] Starting query parameter authentication")

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials. Please provide a valid token.",
    )

    if not token:
        logger.warning("❌ [AUTH-QUERY] No token provided in query parameter")
        raise credentials_exception

    # Log token info (first/last 10 chars only for security)
    token_preview = (
        f"{token[:10]}...{token[-10:]}" if len(token) > 20 else "TOKEN_TOO_SHORT"
    )
    logger.debug(f"🔑 [AUTH-QUERY] Token received: {token_preview}")

    # Decode token
    payload = decode_access_token(token)
    if payload is None:
        logger.warning(f"❌ [AUTH-QUERY] Token decode failed for: {token_preview}")
        raise credentials_exception

    logger.debug(f"✅ [AUTH-QUERY] Token decoded successfully. Payload: {payload}")

    user_id: str | None = payload.get("sub")
    if user_id is None:
        logger.warning("❌ [AUTH-QUERY] No 'sub' field in token payload")
        raise credentials_exception

    logger.debug(f"👤 [AUTH-QUERY] User ID from token: {user_id}")

    # Get user from database
    try:
        user = UserService.get_user_by_id(db, int(user_id))
        if user is None:
            logger.warning(
                f"❌ [AUTH-QUERY] User not found in database: user_id={user_id}"
            )
            raise credentials_exception

        logger.debug(
            f"✅ [AUTH-QUERY] User found: {user.email} (id={user.id}, active={user.is_active})"
        )

    except ValueError as e:
        logger.warning(f"❌ [AUTH-QUERY] Invalid user_id format: {user_id} - {e}")
        raise credentials_exception

    if not user.is_active:
        logger.warning(
            f"❌ [AUTH-QUERY] User account is inactive: {user.email} (id={user.id})"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive",
        )

    logger.info(
        f"✅ [AUTH-QUERY] Authentication successful: {user.email} (id={user.id})"
    )
    return user


def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Dependency to ensure the current user is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    return current_user


# Role hierarchy for permission checking
ROLE_HIERARCHY = {
    UserRole.SUPER_ADMIN: 4,
    UserRole.ADMIN: 3,
    UserRole.USER: 2,
    UserRole.GUEST: 1,
}


def require_role(required_role: UserRole):
    """
    Dependency factory for role-based access control.

    Returns a dependency function that checks if the current user has
    the required role or higher in the hierarchy.

    Args:
        required_role: The minimum role required to access the endpoint

    Returns:
        A dependency function that validates the user's role

    Example:
        @router.get("/admin/users")
        async def list_users(
            current_user: Annotated[User, Depends(require_role(UserRole.SUPER_ADMIN))]
        ):
            ...
    """

    def role_checker(
        current_user: Annotated[User, Depends(get_current_active_user)]
    ) -> User:
        user_level = ROLE_HIERARCHY.get(current_user.role, 0)
        required_level = ROLE_HIERARCHY.get(required_role, 0)

        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role.value}",
            )
        return current_user

    return role_checker


# Convenience dependencies for common role checks
def require_super_admin(
    current_user: Annotated[User, Depends(require_role(UserRole.SUPER_ADMIN))]
) -> User:
    """Dependency to require super_admin role."""
    return current_user


def require_admin(
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))]
) -> User:
    """Dependency to require admin role or higher."""
    return current_user


def require_user(
    current_user: Annotated[User, Depends(require_role(UserRole.USER))]
) -> User:
    """Dependency to require user role or higher."""
    return current_user


# --- Permission-Based Authorization ---


def require_permission(permission_name: str):
    """
    Dependency factory for permission-based access control.

    Checks if the user's role has the specified permission in the database.

    Args:
        permission_name: Permission name (e.g., "user.read", "role.create")

    Returns:
        A dependency function that validates the user's permission

    Example:
        @router.get("/users")
        async def list_users(
            current_user: Annotated[User, Depends(require_permission("user.read"))]
        ):
            ...
    """

    def permission_checker(
        db: Annotated[Session, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        if not PermissionChecker.has_permission(db, current_user, permission_name):
            logger.warning(
                f"❌ [PERMISSION] User {current_user.email} denied access - missing permission: {permission_name}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {permission_name}",
            )
        logger.debug(
            f"✅ [PERMISSION] User {current_user.email} has permission: {permission_name}"
        )
        return current_user

    return permission_checker


def require_any_permission(*permission_names: str):
    """
    Dependency factory requiring ANY of the specified permissions.

    Args:
        *permission_names: Variable number of permission names

    Returns:
        A dependency function that validates the user has at least one permission

    Example:
        @router.get("/users")
        async def list_users(
            current_user: Annotated[User, Depends(require_any_permission("user.read", "admin.full_access"))]
        ):
            ...
    """

    def permission_checker(
        db: Annotated[Session, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        if not PermissionChecker.has_any_permission(
            db, current_user, list(permission_names)
        ):
            logger.warning(
                f"❌ [PERMISSION] User {current_user.email} denied access - missing any of: {permission_names}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required any of: {', '.join(permission_names)}",
            )
        logger.debug(
            f"✅ [PERMISSION] User {current_user.email} has at least one permission from: {permission_names}"
        )
        return current_user

    return permission_checker


def require_all_permissions(*permission_names: str):
    """
    Dependency factory requiring ALL of the specified permissions.

    Args:
        *permission_names: Variable number of permission names

    Returns:
        A dependency function that validates the user has all permissions

    Example:
        @router.post("/users")
        async def create_user(
            current_user: Annotated[User, Depends(require_all_permissions("user.create", "user.update"))]
        ):
            ...
    """

    def permission_checker(
        db: Annotated[Session, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        if not PermissionChecker.has_all_permissions(
            db, current_user, list(permission_names)
        ):
            logger.warning(
                f"❌ [PERMISSION] User {current_user.email} denied access - missing some of: {permission_names}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required all of: {', '.join(permission_names)}",
            )
        logger.debug(
            f"✅ [PERMISSION] User {current_user.email} has all permissions: {permission_names}"
        )
        return current_user

    return permission_checker
