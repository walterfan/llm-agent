"""Admin endpoints for user management."""

import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_active_user,
    get_db,
    require_super_admin,
    require_permission,
)
from app.models.user import User, UserRole
from app.schemas.email import EmailPreferencesResponse, EmailPreferencesUpdate
from app.schemas.user import (
    RoleUpdateRequest,
    UserAdminCreate,
    UserAdminResponse,
    UserAdminUpdate,
    UserListResponse,
)
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/users", response_model=UserListResponse)
def list_users(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission("user.read"))],
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max number of records to return"),
    search: str | None = Query(None, description="Search by email or full name"),
    role: UserRole | None = Query(None, description="Filter by role"),
) -> UserListResponse:
    """
    List all users with pagination and filtering.

    Requires: super_admin role
    """
    logger.info(
        f"Admin {current_user.email} listing users (skip={skip}, limit={limit}, search={search}, role={role})"
    )

    users, total = UserService.get_users(
        db, skip=skip, limit=limit, search=search, role=role
    )

    return UserListResponse(
        items=[UserAdminResponse.model_validate(user) for user in users],
        total=total,
        limit=limit,
        offset=skip,
    )


@router.post(
    "/users", response_model=UserAdminResponse, status_code=status.HTTP_201_CREATED
)
def create_user(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission("user.create"))],
    user_create: UserAdminCreate,
) -> UserAdminResponse:
    """
    Create a new user as admin.

    Requires: super_admin role
    """
    logger.info(f"Admin {current_user.email} creating user: {user_create.email}")

    try:
        user = UserService.create_user_as_admin(db, user_create)
        logger.info(
            f"User created successfully: {user.email} (id={user.id}, role={user.role.value})"
        )
        return UserAdminResponse.model_validate(user)
    except ValueError as e:
        logger.warning(f"Failed to create user: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/users/{user_id}", response_model=UserAdminResponse)
def get_user(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission("user.read"))],
    user_id: int,
) -> UserAdminResponse:
    """
    Get user by ID.

    Requires: super_admin role
    """
    logger.info(f"Admin {current_user.email} getting user: {user_id}")

    user = UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserAdminResponse.model_validate(user)


@router.patch("/users/{user_id}", response_model=UserAdminResponse)
def update_user(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission("user.update"))],
    user_id: int,
    user_update: UserAdminUpdate,
) -> UserAdminResponse:
    """
    Update user as admin.

    Requires: super_admin role
    """
    logger.info(f"Admin {current_user.email} updating user: {user_id}")

    try:
        user = UserService.update_user_as_admin(db, user_id, user_update, current_user)
        logger.info(f"User updated successfully: {user.email} (id={user.id})")
        return UserAdminResponse.model_validate(user)
    except ValueError as e:
        logger.warning(f"Failed to update user: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.patch("/users/{user_id}/role", response_model=UserAdminResponse)
def update_user_role(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission("user.update"))],
    user_id: int,
    role_update: RoleUpdateRequest,
) -> UserAdminResponse:
    """
    Update user role.

    Requires: super_admin role
    """
    logger.info(
        f"Admin {current_user.email} updating role for user {user_id} to {role_update.role.value}"
    )

    try:
        user = UserService.update_user_role(db, user_id, role_update.role, current_user)
        logger.info(
            f"User role updated successfully: {user.email} (id={user.id}, role={user.role.value})"
        )
        return UserAdminResponse.model_validate(user)
    except ValueError as e:
        logger.warning(f"Failed to update user role: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission("user.delete"))],
    user_id: int,
) -> None:
    """
    Delete user as admin.

    Requires: super_admin role
    """
    logger.info(f"Admin {current_user.email} deleting user: {user_id}")

    try:
        UserService.delete_user_as_admin(db, user_id, current_user)
        logger.info(f"User deleted successfully: user_id={user_id}")
    except ValueError as e:
        logger.warning(f"Failed to delete user: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# Email Preferences Management


@router.get(
    "/users/{user_id}/email-preferences", response_model=EmailPreferencesResponse
)
def get_user_email_preferences(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission("user.read"))],
    user_id: int,
) -> EmailPreferencesResponse:
    """
    Get email notification preferences for a specific user (admin only).

    Allows admins to view any user's email preferences.

    Requires: user.read permission (admin or super_admin)
    """
    logger.info(
        f"Admin {current_user.email} getting email preferences for user {user_id}"
    )

    # Get target user
    user = UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    # Get preferences
    preferences = UserService.get_email_preferences(db, user)
    return EmailPreferencesResponse(**preferences)


@router.patch(
    "/users/{user_id}/email-preferences", response_model=EmailPreferencesResponse
)
def update_user_email_preferences(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission("user.update"))],
    user_id: int,
    preferences_update: EmailPreferencesUpdate,
) -> EmailPreferencesResponse:
    """
    Update email notification preferences for a specific user (admin only).

    Allows admins to configure email schedules for any user.

    Requires: user.update permission (admin or super_admin)
    """
    logger.info(
        f"Admin {current_user.email} updating email preferences for user {user_id}"
    )

    # Get target user
    user = UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    # Update preferences
    try:
        updated_user = UserService.update_email_preferences(
            db, user, preferences_update
        )
        preferences = UserService.get_email_preferences(db, updated_user)
        logger.info(
            f"Email preferences updated for user {user_id}: "
            f"enabled={preferences['email_notifications_enabled']}, "
            f"send_time={preferences['email_send_time']}"
        )
        return EmailPreferencesResponse(**preferences)
    except ValueError as e:
        logger.warning(f"Failed to update email preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/users/{user_id}/test-scheduled-email", status_code=status.HTTP_202_ACCEPTED
)
async def test_scheduled_email(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission("user.update"))],
    user_id: int,
) -> dict:
    """
    Test scheduled email for a specific user (admin only).

    Sends a test scheduled email immediately to verify configuration.
    This bypasses the normal schedule and sends the email right away.

    Requires: user.update permission (admin or super_admin)
    """
    logger.info(
        f"Admin {current_user.email} triggering test scheduled email for user {user_id}"
    )

    # Get target user
    user = UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    # Validate user has email preferences configured
    if not user.email_notifications_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email notifications are disabled for this user",
        )

    if not user.preferred_city:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has no preferred_city configured",
        )

    # Send test email using ScheduledEmailService
    try:
        from app.services.scheduled_email_service import ScheduledEmailService

        service = ScheduledEmailService(db)

        # Run async method in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(service.send_scheduled_email(user_id))
        finally:
            loop.close()

        if result["status"] == "error":
            logger.error(f"Test email failed for user {user_id}: {result.get('error')}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send test email: {result.get('error', 'Unknown error')}",
            )

        logger.info(
            f"Test email sent for user {user_id}: "
            f"{result.get('emails_sent', 0)} sent, {result.get('emails_failed', 0)} failed"
        )

        return {
            "message": "Test email sent successfully",
            "user_id": user_id,
            "emails_sent": result.get("emails_sent", 0),
            "emails_failed": result.get("emails_failed", 0),
            "total_recipients": result.get("total_recipients", 0),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending test email for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send test email: {str(e)}",
        )
