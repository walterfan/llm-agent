import logging
from enum import Enum
from typing import NamedTuple

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.security import get_password_hash, verify_password
from app.models.user import User, UserRole
from app.schemas.email import EmailPreferencesUpdate
from app.schemas.user import (
    UserAdminCreate,
    UserAdminUpdate,
    UserCreate,
    UserProfileUpdate,
    UserUpdate,
)

logger = logging.getLogger(__name__)


class AuthFailureReason(str, Enum):
    """Enum for authentication failure reasons."""

    USER_NOT_FOUND = "user_not_found"
    INVALID_PASSWORD = "invalid_password"
    INACTIVE_ACCOUNT = "inactive_account"


class AuthResult(NamedTuple):
    """Result of authentication attempt."""

    user: User | None
    failure_reason: AuthFailureReason | None = None


class UserService:
    """Service for user-related business logic."""

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> User | None:
        """Get user by email address."""
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> User | None:
        """Get user by ID."""
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def create_user(db: Session, user_create: UserCreate) -> User:
        """
        Create a new user via signup.

        - First user automatically becomes super_admin with is_active=True
        - Subsequent users get user role with is_active=False (requires admin approval)
        """
        hashed_password = get_password_hash(user_create.password)

        # Check if this is the first user (for fresh installations)
        user_count = db.query(User).count()

        if user_count == 0:
            # First user: super_admin and active
            role = UserRole.SUPER_ADMIN
            is_active = True
        else:
            # Subsequent users: user role and inactive (requires approval)
            role = UserRole.USER
            is_active = False

        db_user = User(
            email=user_create.email,
            hashed_password=hashed_password,
            full_name=user_create.full_name,
            role=role,
            is_active=is_active,
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> User | None:
        """
        Authenticate user with email and password.

        Returns the user if authentication is successful, None otherwise.
        For detailed failure reasons, use authenticate_user_with_reason().
        """
        result = UserService.authenticate_user_with_reason(db, email, password)
        return result.user

    @staticmethod
    def authenticate_user_with_reason(
        db: Session, email: str, password: str
    ) -> AuthResult:
        """
        Authenticate user with email and password, returning detailed failure reason.

        Returns:
            AuthResult with user and failure_reason
        """
        logger.info(f"🔐 [AUTH] Signin attempt for email: {email}")

        user = UserService.get_user_by_email(db, email)
        if not user:
            logger.warning(f"❌ [AUTH] User not found: {email}")
            return AuthResult(
                user=None, failure_reason=AuthFailureReason.USER_NOT_FOUND
            )

        if not verify_password(password, user.hashed_password):
            logger.warning(
                f"❌ [AUTH] Invalid password for user: {email} (user_id={user.id})"
            )
            return AuthResult(
                user=None, failure_reason=AuthFailureReason.INVALID_PASSWORD
            )

        if not user.is_active:
            logger.warning(
                f"⚠️ [AUTH] Inactive account login attempt: {email} (user_id={user.id}, role={user.role.value})"
            )
            return AuthResult(
                user=None, failure_reason=AuthFailureReason.INACTIVE_ACCOUNT
            )

        logger.info(
            f"✅ [AUTH] Successful authentication for: {email} (user_id={user.id}, role={user.role.value})"
        )
        return AuthResult(user=user, failure_reason=None)

    @staticmethod
    def update_user(db: Session, user: User, user_update: UserUpdate) -> User:
        """Update user information."""
        if user_update.full_name is not None:
            user.full_name = user_update.full_name
        if user_update.password is not None:
            user.hashed_password = get_password_hash(user_update.password)

        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def change_password(
        db: Session, user: User, current_password: str, new_password: str
    ) -> tuple[bool, str]:
        """
        Change user password after verifying current password.

        Returns:
            tuple[bool, str]: (success, message)
        """
        logger.info(
            f"🔐 [PASSWORD] Change password attempt for user: {user.email} (id={user.id})"
        )

        # Verify current password
        if not verify_password(current_password, user.hashed_password):
            logger.warning(
                f"❌ [PASSWORD] Current password verification failed for: {user.email}"
            )
            return False, "Current password is incorrect"

        # Update to new password
        user.hashed_password = get_password_hash(new_password)
        db.add(user)
        db.commit()
        db.refresh(user)

        logger.info(f"✅ [PASSWORD] Password changed successfully for: {user.email}")
        return True, "Password changed successfully"

    @staticmethod
    def update_user_profile(
        db: Session, user: User, profile_update: UserProfileUpdate
    ) -> User:
        """Update user dress preferences profile."""
        update_data = profile_update.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(user, key, value)

        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def delete_user(db: Session, user: User) -> None:
        """Delete a user."""
        db.delete(user)
        db.commit()

    @staticmethod
    def get_email_preferences(db: Session, user: User) -> dict:
        """Get user email preferences."""
        send_time_str = None
        if user.email_send_time:
            send_time_str = user.email_send_time.strftime("%H:%M")
        return {
            "email_notifications_enabled": user.email_notifications_enabled,
            "email_send_time": send_time_str,
            "email_additional_recipients": user.email_additional_recipients or [],
            "email_preferred_city": user.email_preferred_city,
        }

    @staticmethod
    def update_email_preferences(
        db: Session, user: User, preferences: EmailPreferencesUpdate
    ) -> User:
        """Update user email preferences."""
        if preferences.email_notifications_enabled is not None:
            user.email_notifications_enabled = preferences.email_notifications_enabled
        if preferences.email_send_time is not None:
            user.email_send_time = preferences.email_send_time
        if preferences.email_additional_recipients is not None:
            user.email_additional_recipients = preferences.email_additional_recipients
        if preferences.email_preferred_city is not None:
            user.email_preferred_city = preferences.email_preferred_city

        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    # Admin operations
    @staticmethod
    def get_users(
        db: Session,
        skip: int = 0,
        limit: int = 20,
        search: str | None = None,
        role: UserRole | None = None,
    ) -> tuple[list[User], int]:
        """
        Get paginated list of users with optional filtering.

        Returns: (users, total_count)
        """
        query = db.query(User)

        # Apply search filter
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                (User.email.ilike(search_pattern))
                | (User.full_name.ilike(search_pattern))
            )

        # Apply role filter
        if role:
            query = query.filter(User.role == role)

        # Get total count before pagination
        total = query.count()

        # Apply pagination and sorting
        users = query.order_by(User.id).offset(skip).limit(limit).all()

        return users, total

    @staticmethod
    def create_user_as_admin(db: Session, user_create: UserAdminCreate) -> User:
        """
        Create a new user as admin (can specify role).
        """
        # Check if email already exists
        existing_user = UserService.get_user_by_email(db, user_create.email)
        if existing_user:
            raise ValueError("Email already registered")

        hashed_password = get_password_hash(user_create.password)

        db_user = User(
            email=user_create.email,
            hashed_password=hashed_password,
            full_name=user_create.full_name,
            role=user_create.role,
            is_active=user_create.is_active,
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    @staticmethod
    def update_user_as_admin(
        db: Session, user_id: int, user_update: UserAdminUpdate, current_user: User
    ) -> User:
        """
        Update user as admin.

        Validates that:
        - User cannot change their own role
        - Cannot update non-existent user
        """
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            raise ValueError("User not found")

        # Prevent self-role-change (only if actually changing the role)
        if (
            user_update.role is not None
            and user.id == current_user.id
            and user_update.role != user.role
        ):
            raise ValueError("Cannot change your own role")

        # Update fields
        if user_update.full_name is not None:
            user.full_name = user_update.full_name
        if user_update.email is not None:
            # Check if new email is already taken
            existing = (
                db.query(User)
                .filter(User.email == user_update.email, User.id != user_id)
                .first()
            )
            if existing:
                raise ValueError("Email already in use")
            user.email = user_update.email
        if user_update.role is not None:
            user.role = user_update.role
        if user_update.is_active is not None:
            user.is_active = user_update.is_active
        if user_update.password is not None:
            user.hashed_password = get_password_hash(user_update.password)

        # Update profile fields (only if explicitly included in the update)
        profile_fields = [
            "gender",
            "age",
            "identity",
            "style",
            "temperature_sensitivity",
            "activity_context",
            "other_preferences",
        ]

        update_data = user_update.model_dump(exclude_unset=True)

        for field in profile_fields:
            if field in update_data:
                setattr(user, field, update_data[field])

        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def update_user_role(
        db: Session, user_id: int, new_role: UserRole, current_user: User
    ) -> User:
        """
        Update user role.

        Validates that:
        - User cannot change their own role
        - Cannot demote the last super_admin
        """
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            raise ValueError("User not found")

        # Prevent self-role-change
        if user.id == current_user.id:
            raise ValueError("Cannot change your own role")

        # Prevent demoting last super_admin
        if user.role == UserRole.SUPER_ADMIN:
            super_admin_count = (
                db.query(func.count(User.id))
                .filter(User.role == UserRole.SUPER_ADMIN)
                .scalar()
            )
            if super_admin_count <= 1:
                raise ValueError("Cannot demote the last super_admin")

        user.role = new_role
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def delete_user_as_admin(db: Session, user_id: int, current_user: User) -> None:
        """
        Delete user as admin.

        Validates that:
        - User cannot delete themselves
        - Cannot delete the last super_admin
        """
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            raise ValueError("User not found")

        # Prevent self-deletion
        if user.id == current_user.id:
            raise ValueError("Cannot delete your own account")

        # Prevent deleting last super_admin
        if user.role == UserRole.SUPER_ADMIN:
            super_admin_count = (
                db.query(func.count(User.id))
                .filter(User.role == UserRole.SUPER_ADMIN)
                .scalar()
            )
            if super_admin_count <= 1:
                raise ValueError("Cannot delete the last super_admin")

        db.delete(user)
        db.commit()
