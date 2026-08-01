"""CLI script to reset user password."""

import argparse
import getpass
import secrets
import string
import sys

from app.core.security import get_password_hash
from app.db.base import SessionLocal
from app.models.user import User, UserRole


def generate_password(length: int = 16) -> str:
    """Generate a secure random password."""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    # Ensure at least one of each type
    password = [
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
        secrets.choice(string.punctuation),
    ]
    # Fill the rest
    password += [secrets.choice(alphabet) for _ in range(length - 4)]
    # Shuffle
    secrets.SystemRandom().shuffle(password)
    return "".join(password)


def list_users(db, role_filter: str | None = None):
    """List all users or filter by role."""
    print("\n" + "=" * 70)
    print("📋 User List")
    print("=" * 70)

    query = db.query(User)
    if role_filter:
        try:
            role = UserRole(role_filter)
            query = query.filter(User.role == role)
        except ValueError:
            print(f"❌ Invalid role: {role_filter}")
            print(f"   Valid roles: {', '.join([r.value for r in UserRole])}")
            return

    users = query.order_by(User.id).all()

    if not users:
        print("No users found.")
        return

    print(f"{'ID':<5} {'Email':<35} {'Role':<15} {'Active':<8} {'Name'}")
    print("-" * 70)
    for user in users:
        active_status = "✅" if user.is_active else "❌"
        name = user.full_name or "(no name)"
        print(
            f"{user.id:<5} {user.email:<35} {user.role.value:<15} {active_status:<8} {name}"
        )

    print(f"\nTotal: {len(users)} user(s)\n")


def reset_password(
    db, email: str, new_password: str | None = None, activate: bool = False
):
    """Reset password for a user by email."""
    print("\n" + "=" * 60)
    print("🔐 Password Reset")
    print("=" * 60)

    # Find user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        print(f"\n❌ User not found: {email}")
        print("   Use --list to see all users")
        return False

    print(f"\n👤 User found:")
    print(f"   ID:     {user.id}")
    print(f"   Email:  {user.email}")
    print(f"   Name:   {user.full_name or '(no name)'}")
    print(f"   Role:   {user.role.value}")
    print(f"   Active: {'Yes' if user.is_active else 'No'}")

    # Get new password
    if new_password is None:
        # Prompt for password interactively
        print("\n📝 Enter new password (or press Enter to generate one):")
        new_password = getpass.getpass("   New password: ")

        if not new_password:
            new_password = generate_password()
            print(f"\n🔑 Generated password: {new_password}")
        else:
            # Confirm password
            confirm = getpass.getpass("   Confirm password: ")
            if new_password != confirm:
                print("\n❌ Passwords do not match!")
                return False

    # Validate password length
    if len(new_password) < 8:
        print("\n❌ Password must be at least 8 characters!")
        return False

    # Update password
    user.hashed_password = get_password_hash(new_password)

    # Optionally activate user
    if activate and not user.is_active:
        user.is_active = True
        print("\n✅ User activated!")

    db.commit()

    print(f"\n✅ Password updated successfully for: {email}")
    if not user.is_active:
        print(
            "⚠️  Note: User account is still inactive. Use --activate to enable login."
        )

    return True


def activate_user(db, email: str, deactivate: bool = False):
    """Activate or deactivate a user account."""
    action = "Deactivation" if deactivate else "Activation"
    print("\n" + "=" * 60)
    print(f"👤 User {action}")
    print("=" * 60)

    user = db.query(User).filter(User.email == email).first()
    if not user:
        print(f"\n❌ User not found: {email}")
        return False

    if deactivate:
        if not user.is_active:
            print(f"\n⚠️  User is already inactive: {email}")
            return True
        user.is_active = False
        print(f"\n✅ User deactivated: {email}")
    else:
        if user.is_active:
            print(f"\n⚠️  User is already active: {email}")
            return True
        user.is_active = True
        print(f"\n✅ User activated: {email}")

    db.commit()
    return True


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Reset user password or manage user accounts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all users
  python -m app.scripts.reset_password --list
  
  # List only admin users
  python -m app.scripts.reset_password --list --role super_admin
  
  # Reset password interactively (will prompt for password)
  python -m app.scripts.reset_password --email admin@example.com
  
  # Reset password with auto-generated password
  python -m app.scripts.reset_password --email admin@example.com --generate
  
  # Reset password with specific password
  python -m app.scripts.reset_password --email admin@example.com --password "NewPass123!"
  
  # Reset password and activate the user
  python -m app.scripts.reset_password --email admin@example.com --generate --activate
  
  # Only activate a user (no password change)
  python -m app.scripts.reset_password --email user@example.com --activate-only
  
  # Deactivate a user
  python -m app.scripts.reset_password --email user@example.com --deactivate
        """,
    )

    parser.add_argument("--list", "-l", action="store_true", help="List all users")
    parser.add_argument(
        "--role",
        "-r",
        type=str,
        choices=[r.value for r in UserRole],
        help="Filter users by role (used with --list)",
    )
    parser.add_argument("--email", "-e", type=str, help="User email address")
    parser.add_argument(
        "--password",
        "-p",
        type=str,
        help="New password (if not provided, will prompt interactively)",
    )
    parser.add_argument(
        "--generate",
        "-g",
        action="store_true",
        help="Generate a random secure password",
    )
    parser.add_argument(
        "--activate",
        "-a",
        action="store_true",
        help="Also activate the user account after password reset",
    )
    parser.add_argument(
        "--activate-only",
        action="store_true",
        help="Only activate the user (no password change)",
    )
    parser.add_argument(
        "--deactivate", action="store_true", help="Deactivate the user account"
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.list and not args.email:
        parser.print_help()
        print("\n❌ Error: Either --list or --email is required")
        sys.exit(1)

    if args.activate_only and args.deactivate:
        print("❌ Error: Cannot use --activate-only and --deactivate together")
        sys.exit(1)

    # Connect to database
    db = SessionLocal()

    try:
        if args.list:
            list_users(db, args.role)
        elif args.activate_only:
            success = activate_user(db, args.email)
            sys.exit(0 if success else 1)
        elif args.deactivate:
            success = activate_user(db, args.email, deactivate=True)
            sys.exit(0 if success else 1)
        else:
            # Password reset
            new_password = args.password
            if args.generate:
                new_password = generate_password()
                print(f"\n🔑 Generated password: {new_password}")

            success = reset_password(db, args.email, new_password, args.activate)
            sys.exit(0 if success else 1)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
