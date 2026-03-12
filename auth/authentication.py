"""
Authentication Manager
"""
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

import sys
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])

from database.db import DatabaseManager
from database.models import User, UserRole
from auth.utils import (
    hash_password, verify_password, generate_token,
    validate_email, validate_password, validate_username
)
from config import DEFAULT_ADMIN_EMAIL, DEFAULT_ADMIN_PASSWORD


class AuthManager:
    """Authentication operations manager"""

    @staticmethod
    def initialize_admin():
        """Create default admin user if not exists"""
        existing = DatabaseManager.get_user_by_email(DEFAULT_ADMIN_EMAIL)
        if not existing:
            DatabaseManager.create_user(
                email=DEFAULT_ADMIN_EMAIL,
                username="admin",
                password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
                role=UserRole.SUPERADMIN,
                full_name="System Administrator"
            )
            # Mark as verified
            user = DatabaseManager.get_user_by_email(DEFAULT_ADMIN_EMAIL)
            if user:
                DatabaseManager.update_user(user.id, is_verified=True)

    @staticmethod
    def register(
        email: str,
        username: str,
        password: str,
        full_name: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Register a new user
        Returns (success, message, user_data)
        """
        # Validate email
        if not validate_email(email):
            return False, "Invalid email format", None

        # Validate username
        is_valid, msg = validate_username(username)
        if not is_valid:
            return False, msg, None

        # Validate password
        is_valid, msg = validate_password(password)
        if not is_valid:
            return False, msg, None

        # Check if email exists
        if DatabaseManager.get_user_by_email(email):
            return False, "Email already registered", None

        # Check if username exists
        if DatabaseManager.get_user_by_username(username):
            return False, "Username already taken", None

        # Create user
        user = DatabaseManager.create_user(
            email=email,
            username=username,
            password_hash=hash_password(password),
            full_name=full_name
        )

        if user:
            return True, "Registration successful", {
                'id': user.id,
                'email': user.email,
                'username': user.username,
                'role': user.role.value
            }

        return False, "Failed to create user", None

    @staticmethod
    def login(
        email_or_username: str,
        password: str
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Login a user
        Returns (success, message, user_data)
        """
        # Try to find user by email or username
        user = DatabaseManager.get_user_by_email(email_or_username)
        if not user:
            user = DatabaseManager.get_user_by_username(email_or_username)

        if not user:
            return False, "Invalid credentials", None

        if not user.is_active:
            return False, "Account is deactivated", None

        if not verify_password(password, user.password_hash):
            return False, "Invalid credentials", None

        # Update last login
        DatabaseManager.update_user_login(user.id)

        return True, "Login successful", {
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'full_name': user.full_name,
            'role': user.role.value,
            'is_verified': user.is_verified
        }

    @staticmethod
    def request_password_reset(email: str) -> Tuple[bool, str, Optional[str]]:
        """
        Request password reset
        Returns (success, message, reset_token)
        """
        user = DatabaseManager.get_user_by_email(email)
        if not user:
            # Return success to prevent email enumeration
            return True, "If the email exists, a reset link will be sent", None

        token = generate_token()
        DatabaseManager.set_reset_token(user.id, token)

        return True, "Reset token generated", token

    @staticmethod
    def reset_password(token: str, new_password: str) -> Tuple[bool, str]:
        """
        Reset password using token
        Returns (success, message)
        """
        user = DatabaseManager.verify_reset_token(token)
        if not user:
            return False, "Invalid or expired reset token"

        # Validate new password
        is_valid, msg = validate_password(new_password)
        if not is_valid:
            return False, msg

        # Update password
        DatabaseManager.update_user(
            user.id,
            password_hash=hash_password(new_password)
        )
        DatabaseManager.clear_reset_token(user.id)

        return True, "Password reset successful"

    @staticmethod
    def change_password(
        user_id: int,
        current_password: str,
        new_password: str
    ) -> Tuple[bool, str]:
        """
        Change password for logged-in user
        Returns (success, message)
        """
        user = DatabaseManager.get_user_by_id(user_id)
        if not user:
            return False, "User not found"

        if not verify_password(current_password, user.password_hash):
            return False, "Current password is incorrect"

        # Validate new password
        is_valid, msg = validate_password(new_password)
        if not is_valid:
            return False, msg

        # Update password
        DatabaseManager.update_user(
            user_id,
            password_hash=hash_password(new_password)
        )

        return True, "Password changed successfully"

    @staticmethod
    def update_profile(
        user_id: int,
        full_name: Optional[str] = None,
        avatar_url: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Update user profile
        Returns (success, message)
        """
        updates = {}
        if full_name is not None:
            updates['full_name'] = full_name
        if avatar_url is not None:
            updates['avatar_url'] = avatar_url

        if not updates:
            return False, "No updates provided"

        success = DatabaseManager.update_user(user_id, **updates)
        if success:
            return True, "Profile updated successfully"
        return False, "Failed to update profile"

    @staticmethod
    def get_user_info(user_id: int) -> Optional[Dict[str, Any]]:
        """Get user information"""
        user = DatabaseManager.get_user_by_id(user_id)
        if not user:
            return None

        return {
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'full_name': user.full_name,
            'role': user.role.value,
            'is_active': user.is_active,
            'is_verified': user.is_verified,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'last_login': user.last_login.isoformat() if user.last_login else None
        }

    # ==================== Admin Operations ====================

    @staticmethod
    def is_admin(user_id: int) -> bool:
        """Check if user is admin"""
        user = DatabaseManager.get_user_by_id(user_id)
        if not user:
            return False
        return user.role in [UserRole.ADMIN, UserRole.SUPERADMIN]

    @staticmethod
    def is_superadmin(user_id: int) -> bool:
        """Check if user is superadmin"""
        user = DatabaseManager.get_user_by_id(user_id)
        if not user:
            return False
        return user.role == UserRole.SUPERADMIN

    @staticmethod
    def get_all_users() -> list:
        """Get all users (admin only)"""
        users = DatabaseManager.get_all_users()
        return [
            {
                'id': u.id,
                'email': u.email,
                'username': u.username,
                'full_name': u.full_name,
                'role': u.role.value,
                'is_active': u.is_active,
                'is_verified': u.is_verified,
                'created_at': u.created_at.isoformat() if u.created_at else None,
                'last_login': u.last_login.isoformat() if u.last_login else None
            }
            for u in users
        ]

    @staticmethod
    def admin_update_user(
        admin_id: int,
        user_id: int,
        **kwargs
    ) -> Tuple[bool, str]:
        """
        Admin update user
        Returns (success, message)
        """
        if not AuthManager.is_admin(admin_id):
            return False, "Permission denied"

        # Prevent self-demotion for superadmin
        admin = DatabaseManager.get_user_by_id(admin_id)
        target = DatabaseManager.get_user_by_id(user_id)

        if not target:
            return False, "User not found"

        # Superadmin protection
        if target.role == UserRole.SUPERADMIN and admin_id != user_id:
            return False, "Cannot modify superadmin"

        # Handle role change
        if 'role' in kwargs:
            if not AuthManager.is_superadmin(admin_id):
                return False, "Only superadmin can change roles"
            kwargs['role'] = UserRole(kwargs['role'])

        # Handle password change
        if 'password' in kwargs:
            kwargs['password_hash'] = hash_password(kwargs.pop('password'))

        success = DatabaseManager.update_user(user_id, **kwargs)
        if success:
            return True, "User updated successfully"
        return False, "Failed to update user"

    @staticmethod
    def admin_delete_user(admin_id: int, user_id: int) -> Tuple[bool, str]:
        """
        Admin delete user
        Returns (success, message)
        """
        if not AuthManager.is_superadmin(admin_id):
            return False, "Only superadmin can delete users"

        if admin_id == user_id:
            return False, "Cannot delete yourself"

        target = DatabaseManager.get_user_by_id(user_id)
        if not target:
            return False, "User not found"

        if target.role == UserRole.SUPERADMIN:
            return False, "Cannot delete superadmin"

        success = DatabaseManager.delete_user(user_id)
        if success:
            return True, "User deleted successfully"
        return False, "Failed to delete user"

    @staticmethod
    def admin_toggle_user_status(
        admin_id: int,
        user_id: int
    ) -> Tuple[bool, str]:
        """
        Toggle user active status
        Returns (success, message)
        """
        if not AuthManager.is_admin(admin_id):
            return False, "Permission denied"

        if admin_id == user_id:
            return False, "Cannot deactivate yourself"

        target = DatabaseManager.get_user_by_id(user_id)
        if not target:
            return False, "User not found"

        if target.role == UserRole.SUPERADMIN:
            return False, "Cannot modify superadmin"

        new_status = not target.is_active
        success = DatabaseManager.update_user(user_id, is_active=new_status)

        if success:
            status_text = "activated" if new_status else "deactivated"
            return True, f"User {status_text} successfully"
        return False, "Failed to update user status"
