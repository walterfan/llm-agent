"""RBAC (Role-Based Access Control) schemas."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


# Permission Schemas
class PermissionBase(BaseModel):
    """Base permission schema."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Permission name (e.g., 'user.create')",
    )
    resource: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Resource type (e.g., 'user', 'recommendation')",
    )
    action: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Action type (e.g., 'create', 'read', 'update', 'delete')",
    )
    description: str | None = Field(None, description="Permission description")


class PermissionCreate(PermissionBase):
    """Schema for creating a permission."""

    pass


class PermissionUpdate(BaseModel):
    """Schema for updating a permission."""

    name: str | None = Field(None, min_length=1, max_length=100)
    resource: str | None = Field(None, min_length=1, max_length=50)
    action: str | None = Field(None, min_length=1, max_length=50)
    description: str | None = None


class Permission(PermissionBase):
    """Schema for permission response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class PermissionListResponse(BaseModel):
    """Schema for paginated permission list response."""

    items: list[Permission]
    total: int
    limit: int
    offset: int


# Role Schemas
class RoleBase(BaseModel):
    """Base role schema."""

    name: str = Field(..., min_length=1, max_length=50, description="Role name")
    description: str | None = Field(None, description="Role description")


class RoleCreate(RoleBase):
    """Schema for creating a role."""

    permission_ids: list[int] = Field(
        default_factory=list, description="List of permission IDs to assign"
    )


class RoleUpdate(BaseModel):
    """Schema for updating a role."""

    name: str | None = Field(None, min_length=1, max_length=50)
    description: str | None = None
    permission_ids: list[int] | None = Field(
        None, description="List of permission IDs to assign (replaces existing)"
    )


class Role(RoleBase):
    """Schema for role response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    permissions: list[Permission] = Field(default_factory=list)


class RoleListResponse(BaseModel):
    """Schema for paginated role list response."""

    items: list[Role]
    total: int
    limit: int
    offset: int


# Role-Permission Assignment
class RolePermissionAssignment(BaseModel):
    """Schema for assigning/removing permissions to/from a role."""

    permission_ids: list[int] = Field(
        ..., min_items=1, description="List of permission IDs"
    )
