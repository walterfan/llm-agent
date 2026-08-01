"""RBAC (Role and Permission) management endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db, require_permission
from app.models.user import User
from app.schemas.rbac import (
    Permission,
    PermissionCreate,
    PermissionListResponse,
    PermissionUpdate,
    Role,
    RoleCreate,
    RoleListResponse,
    RolePermissionAssignment,
    RoleUpdate,
)
from app.services.rbac_service import PermissionService, RoleService

logger = logging.getLogger(__name__)

router = APIRouter()


# Permission Endpoints
@router.get("/permissions", response_model=PermissionListResponse)
def list_permissions(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission("permission.read"))],
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max number of records to return"),
    resource: str | None = Query(None, description="Filter by resource type"),
) -> PermissionListResponse:
    """
    List all permissions with pagination and filtering.

    Requires: permission.read permission
    """
    logger.info(
        f"Admin {current_user.email} listing permissions (skip={skip}, limit={limit}, resource={resource})"
    )

    permissions, total = PermissionService.get_permissions(
        db, skip=skip, limit=limit, resource=resource
    )

    return PermissionListResponse(
        items=[Permission.model_validate(p) for p in permissions],
        total=total,
        limit=limit,
        offset=skip,
    )


@router.post(
    "/permissions", response_model=Permission, status_code=status.HTTP_201_CREATED
)
def create_permission(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission("permission.create"))],
    permission_create: PermissionCreate,
) -> Permission:
    """
    Create a new permission.

    Requires: permission.create permission
    """
    logger.info(
        f"Admin {current_user.email} creating permission: {permission_create.name}"
    )

    try:
        permission = PermissionService.create_permission(db, permission_create)
        logger.info(
            f"Permission created successfully: {permission.name} (id={permission.id})"
        )
        return Permission.model_validate(permission)
    except ValueError as e:
        logger.warning(f"Failed to create permission: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/permissions/{permission_id}", response_model=Permission)
def get_permission(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission("permission.read"))],
    permission_id: int,
) -> Permission:
    """
    Get permission by ID.

    Requires: permission.read permission
    """
    logger.info(f"Admin {current_user.email} getting permission: {permission_id}")

    permission = PermissionService.get_permission_by_id(db, permission_id)
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found",
        )

    return Permission.model_validate(permission)


@router.patch("/permissions/{permission_id}", response_model=Permission)
def update_permission(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission("permission.update"))],
    permission_id: int,
    permission_update: PermissionUpdate,
) -> Permission:
    """
    Update permission.

    Requires: permission.update permission
    """
    logger.info(f"Admin {current_user.email} updating permission: {permission_id}")

    try:
        permission = PermissionService.update_permission(
            db, permission_id, permission_update
        )
        logger.info(
            f"Permission updated successfully: {permission.name} (id={permission.id})"
        )
        return Permission.model_validate(permission)
    except ValueError as e:
        logger.warning(f"Failed to update permission: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/permissions/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_permission(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission("permission.delete"))],
    permission_id: int,
) -> None:
    """
    Delete permission.

    Requires: permission.delete permission
    """
    logger.info(f"Admin {current_user.email} deleting permission: {permission_id}")

    try:
        PermissionService.delete_permission(db, permission_id)
        logger.info(f"Permission deleted successfully: permission_id={permission_id}")
    except ValueError as e:
        logger.warning(f"Failed to delete permission: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# Role Endpoints
@router.get("/roles", response_model=RoleListResponse)
def list_roles(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission("role.read"))],
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max number of records to return"),
    search: str | None = Query(None, description="Search by role name"),
) -> RoleListResponse:
    """
    List all roles with pagination and search.

    Requires: role.read permission
    """
    logger.info(
        f"Admin {current_user.email} listing roles (skip={skip}, limit={limit}, search={search})"
    )

    roles, total = RoleService.get_roles(db, skip=skip, limit=limit, search=search)

    return RoleListResponse(
        items=[Role.model_validate(r) for r in roles],
        total=total,
        limit=limit,
        offset=skip,
    )


@router.post("/roles", response_model=Role, status_code=status.HTTP_201_CREATED)
def create_role(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission("role.create"))],
    role_create: RoleCreate,
) -> Role:
    """
    Create a new role with permissions.

    Requires: role.create permission
    """
    logger.info(f"Admin {current_user.email} creating role: {role_create.name}")

    try:
        role = RoleService.create_role(db, role_create)
        logger.info(f"Role created successfully: {role.name} (id={role.id})")
        return Role.model_validate(role)
    except ValueError as e:
        logger.warning(f"Failed to create role: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/roles/{role_id}", response_model=Role)
def get_role(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission("role.read"))],
    role_id: int,
) -> Role:
    """
    Get role by ID with permissions.

    Requires: role.read permission
    """
    logger.info(f"Admin {current_user.email} getting role: {role_id}")

    role = RoleService.get_role_by_id(db, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    return Role.model_validate(role)


@router.patch("/roles/{role_id}", response_model=Role)
def update_role(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission("role.update"))],
    role_id: int,
    role_update: RoleUpdate,
) -> Role:
    """
    Update role.

    Requires: role.update permission
    """
    logger.info(f"Admin {current_user.email} updating role: {role_id}")

    try:
        role = RoleService.update_role(db, role_id, role_update)
        logger.info(f"Role updated successfully: {role.name} (id={role.id})")
        return Role.model_validate(role)
    except ValueError as e:
        logger.warning(f"Failed to update role: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission("role.delete"))],
    role_id: int,
) -> None:
    """
    Delete role.

    Requires: role.delete permission
    """
    logger.info(f"Admin {current_user.email} deleting role: {role_id}")

    try:
        RoleService.delete_role(db, role_id)
        logger.info(f"Role deleted successfully: role_id={role_id}")
    except ValueError as e:
        logger.warning(f"Failed to delete role: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/roles/{role_id}/permissions", response_model=Role)
def add_permissions_to_role(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission("role.update"))],
    role_id: int,
    assignment: RolePermissionAssignment,
) -> Role:
    """
    Add permissions to a role.

    Requires: role.update permission
    """
    logger.info(f"Admin {current_user.email} adding permissions to role {role_id}")

    try:
        role = RoleService.add_permissions_to_role(
            db, role_id, assignment.permission_ids
        )
        logger.info(
            f"Permissions added successfully to role: {role.name} (id={role.id})"
        )
        return Role.model_validate(role)
    except ValueError as e:
        logger.warning(f"Failed to add permissions to role: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/roles/{role_id}/permissions", response_model=Role)
def remove_permissions_from_role(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission("role.update"))],
    role_id: int,
    assignment: RolePermissionAssignment,
) -> Role:
    """
    Remove permissions from a role.

    Requires: role.update permission
    """
    logger.info(f"Admin {current_user.email} removing permissions from role {role_id}")

    try:
        role = RoleService.remove_permissions_from_role(
            db, role_id, assignment.permission_ids
        )
        logger.info(
            f"Permissions removed successfully from role: {role.name} (id={role.id})"
        )
        return Role.model_validate(role)
    except ValueError as e:
        logger.warning(f"Failed to remove permissions from role: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
