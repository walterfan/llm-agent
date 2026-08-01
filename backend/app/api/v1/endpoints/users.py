import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.base import get_db
from app.models.user import User as UserModel
from app.schemas.user import ChangePasswordRequest, User, UserProfileUpdate, UserUpdate
from app.services.user_service import UserService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/me", response_model=User)
def get_current_user_profile(
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
) -> User:
    """
    Get current user profile information.

    Requires authentication.
    """
    return User.model_validate(current_user)


@router.patch("/me", response_model=User)
def update_current_user_profile(
    user_update: UserUpdate,
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """
    Update current user profile.

    - **full_name**: update full name
    - **password**: update password (will be hashed)

    Requires authentication.
    """
    updated_user = UserService.update_user(db, current_user, user_update)
    return User.model_validate(updated_user)


@router.patch("/me/profile", response_model=User)
def update_user_dress_profile(
    profile_update: UserProfileUpdate,
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """
    Update user dress preferences profile.

    - **gender**: Gender ('男', '女', '其他')
    - **age**: Age (0-150)
    - **identity**: Identity ('大学生', '上班族', '退休人员', etc.)
    - **style**: Style preference ('舒适优先', '时尚优先', '运动风', '商务风')
    - **temperature_sensitivity**: Temperature sensitivity ('怕冷', '正常', '怕热', '非常怕冷')
    - **activity_context**: Activity context ('工作日', '周末', '假期', '出游', '居家')
    - **other_preferences**: Other preferences (free text, max 1000 chars)

    Requires authentication.
    """
    updated_user = UserService.update_user_profile(db, current_user, profile_update)
    return User.model_validate(updated_user)


@router.post("/me/change-password")
def change_password(
    password_data: ChangePasswordRequest,
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """
    Change current user's password.

    - **current_password**: Current password for verification
    - **new_password**: New password (minimum 8 characters)

    Requires authentication.
    """
    logger.info(f"📥 [API] Change password request for user: {current_user.email}")

    success, message = UserService.change_password(
        db, current_user, password_data.current_password, password_data.new_password
    )

    if not success:
        logger.warning(
            f"📥 [API] Change password failed for: {current_user.email} - {message}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )

    logger.info(f"📥 [API] Password changed successfully for: {current_user.email}")
    return {"message": message}


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_current_user_account(
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """
    Delete current user account.

    This action is irreversible. Requires authentication.
    """
    UserService.delete_user(db, current_user)
