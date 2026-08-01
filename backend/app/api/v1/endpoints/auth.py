import logging
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
)
from app.db.base import get_db
from app.models.user import UserRole
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
    SignupRequest,
    SignupResponse,
)
from app.schemas.user import User, UserCreate
from app.services.user_service import AuthFailureReason, UserService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED
)
def signup(
    signup_data: SignupRequest,
    db: Annotated[Session, Depends(get_db)],
) -> SignupResponse:
    """
    Register a new user.

    - **email**: valid email address (unique)
    - **password**: minimum 8 characters
    - **full_name**: optional full name

    **Note**:
    - First user becomes super_admin and is active immediately
    - Subsequent users are inactive and require admin approval
    """
    # Check if user already exists
    existing_user = UserService.get_user_by_email(db, signup_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create new user
    user_create = UserCreate(
        email=signup_data.email,
        password=signup_data.password,
        full_name=signup_data.full_name,
    )
    user = UserService.create_user(db, user_create)

    # Determine message based on whether this is the first user
    if user.role == UserRole.SUPER_ADMIN:
        message = "User created successfully as super admin"
    else:
        message = "User created successfully. Your account is pending approval by an administrator."

    return SignupResponse(
        user=User.model_validate(user),
        message=message,
    )


@router.post("/signin", response_model=LoginResponse)
def signin(
    login_data: LoginRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> LoginResponse:
    """
    Login with email and password to get access token.

    - **email**: registered email address
    - **password**: user password
    """
    # Log the signin request
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"📥 [SIGNIN] Request from {client_ip} for email: {login_data.email}")

    # Authenticate user with detailed failure reason
    auth_result = UserService.authenticate_user_with_reason(
        db, login_data.email, login_data.password
    )

    if auth_result.user is None:
        # Handle different failure reasons with appropriate messages
        if auth_result.failure_reason == AuthFailureReason.INACTIVE_ACCOUNT:
            logger.warning(
                f"📥 [SIGNIN] Rejected - inactive account: {login_data.email}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account is inactive and pending approval by an administrator. Please contact support.",
            )
        else:
            # For user_not_found and invalid_password, use generic message for security
            logger.warning(
                f"📥 [SIGNIN] Rejected - {auth_result.failure_reason.value}: {login_data.email}"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

    user = auth_result.user
    logger.info(f"📥 [SIGNIN] Success for: {login_data.email} (user_id={user.id})")

    # Create access token and refresh token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=str(user.id),
        expires_delta=access_token_expires,
    )
    refresh_token = create_refresh_token(subject=str(user.id))

    return LoginResponse(
        user=User.model_validate(user),
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/refresh", response_model=RefreshResponse)
def refresh_token(
    request: RefreshRequest,
    db: Annotated[Session, Depends(get_db)],
) -> RefreshResponse:
    """
    Refresh an expired access token using a valid refresh token.

    Returns a new access token and a rotated refresh token.
    """
    payload = decode_access_token(request.refresh_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Verify this is a refresh token, not an access token
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    # Verify user still exists and is active
    user = UserService.get_user_by_id(db, int(user_id))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Issue new tokens (token rotation)
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = create_access_token(
        subject=str(user.id),
        expires_delta=access_token_expires,
    )
    new_refresh_token = create_refresh_token(subject=str(user.id))

    logger.info(f"🔄 [REFRESH] Token refreshed for user_id={user.id}")

    return RefreshResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
    )
