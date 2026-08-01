from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import UserRole


class UserBase(BaseModel):
    """Base user schema with common attributes."""

    email: EmailStr
    full_name: str | None = None


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str = Field(
        ..., min_length=8, description="Password must be at least 8 characters"
    )


class UserProfileUpdate(BaseModel):
    """Schema for updating user profile (dress preferences)."""

    gender: str | None = Field(None, description="Gender: '男', '女', '其他'")
    age: int | None = Field(None, ge=0, le=150, description="Age (0-150)")
    identity: str | None = Field(
        None, description="Identity: '大学生', '上班族', '退休人员', etc."
    )
    style: str | None = Field(
        None, description="Style: '舒适优先', '时尚优先', '运动风', '商务风'"
    )
    temperature_sensitivity: str | None = Field(
        None, description="Temperature sensitivity: '怕冷', '正常', '怕热', '非常怕冷'"
    )
    activity_context: str | None = Field(
        None, description="Activity context: '工作日', '周末', '假期', '出游', '居家'"
    )
    other_preferences: str | None = Field(
        None, max_length=1000, description="Other preferences (free text)"
    )

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: str | None) -> str | None:
        if v is not None:
            allowed = ["男", "女", "其他"]
            if v not in allowed:
                raise ValueError(f"Gender must be one of {allowed}")
        return v

    @field_validator("style")
    @classmethod
    def validate_style(cls, v: str | None) -> str | None:
        if v is not None:
            allowed = ["舒适优先", "时尚优先", "运动风", "商务风"]
            if v not in allowed:
                raise ValueError(f"Style must be one of {allowed}")
        return v

    @field_validator("temperature_sensitivity")
    @classmethod
    def validate_temperature_sensitivity(cls, v: str | None) -> str | None:
        if v is not None:
            allowed = ["怕冷", "正常", "怕热", "非常怕冷"]
            if v not in allowed:
                raise ValueError(f"Temperature sensitivity must be one of {allowed}")
        return v

    @field_validator("activity_context")
    @classmethod
    def validate_activity_context(cls, v: str | None) -> str | None:
        if v is not None:
            allowed = ["工作日", "周末", "假期", "出游", "居家"]
            if v not in allowed:
                raise ValueError(f"Activity context must be one of {allowed}")
        return v


class UserUpdate(BaseModel):
    """Schema for updating user information."""

    full_name: str | None = None
    password: str | None = Field(
        None, min_length=8, description="Password must be at least 8 characters"
    )


class ChangePasswordRequest(BaseModel):
    """Schema for changing user password."""

    current_password: str = Field(..., description="Current password for verification")
    new_password: str = Field(
        ..., min_length=8, description="New password (minimum 8 characters)"
    )


class UserInDB(UserBase):
    """Schema for user as stored in database."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    role: UserRole  # Add role field
    created_at: datetime
    updated_at: datetime

    # Profile fields
    gender: str | None = None
    age: int | None = None
    identity: str | None = None
    style: str | None = None
    temperature_sensitivity: str | None = None
    activity_context: str | None = None
    other_preferences: str | None = None


class User(UserInDB):
    """Schema for user response (public view)."""

    pass


# Admin-specific schemas for user management
class UserAdminCreate(BaseModel):
    """Schema for creating a user as admin."""

    email: EmailStr
    password: str = Field(
        ..., min_length=8, description="Password must be at least 8 characters"
    )
    full_name: str | None = None
    role: UserRole = Field(default=UserRole.USER, description="User role")
    is_active: bool = Field(
        default=True, description="Whether the user account is active"
    )


class UserAdminUpdate(BaseModel):
    """Schema for updating a user as admin."""

    full_name: str | None = None
    email: EmailStr | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    password: str | None = Field(
        None, min_length=8, description="New password (optional)"
    )

    # Profile fields (optional)
    gender: str | None = None
    age: int | None = None
    identity: str | None = None
    style: str | None = None
    temperature_sensitivity: str | None = None
    activity_context: str | None = None
    other_preferences: str | None = None

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: str | None) -> str | None:
        if v is not None:
            allowed = ["男", "女", "其他"]
            if v not in allowed:
                raise ValueError(f"Gender must be one of {allowed}")
        return v

    @field_validator("style")
    @classmethod
    def validate_style(cls, v: str | None) -> str | None:
        if v is not None:
            allowed = ["舒适优先", "时尚优先", "运动风", "商务风"]
            if v not in allowed:
                raise ValueError(f"Style must be one of {allowed}")
        return v

    @field_validator("temperature_sensitivity")
    @classmethod
    def validate_temperature_sensitivity(cls, v: str | None) -> str | None:
        if v is not None:
            allowed = ["怕冷", "正常", "怕热", "非常怕冷"]
            if v not in allowed:
                raise ValueError(f"Temperature sensitivity must be one of {allowed}")
        return v

    @field_validator("activity_context")
    @classmethod
    def validate_activity_context(cls, v: str | None) -> str | None:
        if v is not None:
            allowed = ["工作日", "周末", "假期", "出游", "居家"]
            if v not in allowed:
                raise ValueError(f"Activity context must be one of {allowed}")
        return v


class RoleUpdateRequest(BaseModel):
    """Schema for updating user role."""

    role: UserRole = Field(..., description="New role for the user")


class UserAdminResponse(BaseModel):
    """Schema for user response in admin context (includes all fields)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str | None
    is_active: bool
    role: UserRole
    created_at: datetime
    updated_at: datetime


class UserListResponse(BaseModel):
    """Schema for paginated user list response."""

    items: list[UserAdminResponse]
    total: int
    limit: int
    offset: int


class UserWithPassword(UserInDB):
    """Schema for user with hashed password (internal use only)."""

    hashed_password: str
