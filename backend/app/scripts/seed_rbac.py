"""Seed script for default roles and permissions."""

from app.db.base import SessionLocal
from app.models.permission import Permission
from app.models.role import Role
from app.services.rbac_service import PermissionService, RoleService
from app.schemas.rbac import PermissionCreate, RoleCreate


def seed_permissions(db):
    """Create default permissions."""
    print("📝 Seeding permissions...")

    # Define default permissions
    default_permissions = [
        # User permissions
        {
            "name": "user.read",
            "resource": "user",
            "action": "read",
            "description": "View user information",
        },
        {
            "name": "user.create",
            "resource": "user",
            "action": "create",
            "description": "Create new users",
        },
        {
            "name": "user.update",
            "resource": "user",
            "action": "update",
            "description": "Update user information",
        },
        {
            "name": "user.delete",
            "resource": "user",
            "action": "delete",
            "description": "Delete users",
        },
        # Recommendation permissions
        {
            "name": "recommendation.read",
            "resource": "recommendation",
            "action": "read",
            "description": "View recommendations",
        },
        {
            "name": "recommendation.create",
            "resource": "recommendation",
            "action": "create",
            "description": "Create recommendations",
        },
        {
            "name": "recommendation.admin",
            "resource": "recommendation",
            "action": "admin",
            "description": "Generate recommendations for other users (admin only)",
        },
        # Weather permissions
        {
            "name": "weather.read",
            "resource": "weather",
            "action": "read",
            "description": "View weather information",
        },
        # Email permissions
        {
            "name": "email.read",
            "resource": "email",
            "action": "read",
            "description": "View email logs",
        },
        {
            "name": "email.send",
            "resource": "email",
            "action": "send",
            "description": "Send emails",
        },
        # RBAC permissions
        {
            "name": "role.read",
            "resource": "role",
            "action": "read",
            "description": "View roles",
        },
        {
            "name": "role.create",
            "resource": "role",
            "action": "create",
            "description": "Create roles",
        },
        {
            "name": "role.update",
            "resource": "role",
            "action": "update",
            "description": "Update roles",
        },
        {
            "name": "role.delete",
            "resource": "role",
            "action": "delete",
            "description": "Delete roles",
        },
        {
            "name": "permission.read",
            "resource": "permission",
            "action": "read",
            "description": "View permissions",
        },
        {
            "name": "permission.create",
            "resource": "permission",
            "action": "create",
            "description": "Create permissions",
        },
        {
            "name": "permission.update",
            "resource": "permission",
            "action": "update",
            "description": "Update permissions",
        },
        {
            "name": "permission.delete",
            "resource": "permission",
            "action": "delete",
            "description": "Delete permissions",
        },
    ]

    created_count = 0
    skipped_count = 0

    for perm_data in default_permissions:
        try:
            # Check if permission already exists
            existing = PermissionService.get_permission_by_name(db, perm_data["name"])
            if existing:
                print(f"  ⏭️  Permission '{perm_data['name']}' already exists, skipping")
                skipped_count += 1
                continue

            permission_create = PermissionCreate(**perm_data)
            permission = PermissionService.create_permission(db, permission_create)
            print(f"  ✅ Created permission: {permission.name}")
            created_count += 1
        except Exception as e:
            print(f"  ❌ Failed to create permission '{perm_data['name']}': {e}")

    print(
        f"\n✅ Permissions seeding complete: {created_count} created, {skipped_count} skipped\n"
    )


def seed_roles(db):
    """Create default roles with permissions."""
    print("👥 Seeding roles...")

    # Define default roles and their permissions
    default_roles = [
        {
            "name": "Super Administrator",
            "description": "Full system access with all permissions",
            "permissions": [
                "user.read",
                "user.create",
                "user.update",
                "user.delete",
                "recommendation.read",
                "recommendation.create",
                "recommendation.admin",
                "weather.read",
                "email.read",
                "email.send",
                "role.read",
                "role.create",
                "role.update",
                "role.delete",
                "permission.read",
                "permission.create",
                "permission.update",
                "permission.delete",
            ],
        },
        {
            "name": "Administrator",
            "description": "Administrative access for user and content management",
            "permissions": [
                "user.read",
                "user.update",
                "recommendation.read",
                "recommendation.create",
                "recommendation.admin",
                "weather.read",
                "email.read",
                "email.send",
            ],
        },
        {
            "name": "Regular User",
            "description": "Standard user access for personal features",
            "permissions": [
                "user.read",
                "recommendation.read",
                "recommendation.create",
                "weather.read",
                "email.send",
            ],
        },
        {
            "name": "Guest",
            "description": "Limited read-only access",
            "permissions": [
                "weather.read",
            ],
        },
    ]

    created_count = 0
    skipped_count = 0

    for role_data in default_roles:
        try:
            # Check if role already exists
            existing = RoleService.get_role_by_name(db, role_data["name"])
            if existing:
                print(f"  ⏭️  Role '{role_data['name']}' already exists, skipping")
                skipped_count += 1
                continue

            # Get permission IDs
            permission_names = role_data.pop("permissions")
            permission_ids = []
            for perm_name in permission_names:
                perm = PermissionService.get_permission_by_name(db, perm_name)
                if perm:
                    permission_ids.append(perm.id)
                else:
                    print(f"  ⚠️  Warning: Permission '{perm_name}' not found")

            role_create = RoleCreate(**role_data, permission_ids=permission_ids)
            role = RoleService.create_role(db, role_create)
            print(
                f"  ✅ Created role: {role.name} ({len(role.permissions)} permissions)"
            )
            created_count += 1
        except Exception as e:
            print(f"  ❌ Failed to create role '{role_data['name']}': {e}")

    print(
        f"\n✅ Roles seeding complete: {created_count} created, {skipped_count} skipped\n"
    )


def main():
    """Main seeding function."""
    print("\n" + "=" * 60)
    print("🌱 RBAC Seeding Script")
    print("=" * 60 + "\n")

    db = SessionLocal()

    try:
        # Seed permissions first (required by roles)
        seed_permissions(db)

        # Seed roles with permissions
        seed_roles(db)

        print("=" * 60)
        print("✅ RBAC seeding complete!")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n❌ Seeding failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
