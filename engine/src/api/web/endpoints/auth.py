"""Authentication endpoints."""

import logging
from typing import Dict, Any
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, status, Request

from ...services.auth import (
    fastapi_users,
    auth_backend,
    current_active_user,
    get_user_manager,
    UserManager,
)
from ...domain.models.user import UserCreate, UserRead, UserUpdate, User

logger = logging.getLogger(__name__)
router = APIRouter()

# Register FastAPI Users JWT auth routes
router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/jwt",
    tags=["auth"],
)

# Register FastAPI Users register routes
router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/register",
    tags=["auth"],
)

# Register FastAPI Users verify routes
router.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/verify",
    tags=["auth"],
)

# Register FastAPI Users reset password routes
router.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/reset-password",
    tags=["auth"],
)

# Register FastAPI Users routes for handling user data
router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)


@router.get("/is_admin_user", response_model=Dict[str, bool], tags=["auth"])
async def is_admin_user():
    """Check if any users exist in the database. If none exist, the requester is considered an admin."""
    try:
        # Get the total count of users using the User model directly
        user_count = await User.all().count()
        
        logger.debug(f"Admin user check - User count: {user_count}")
        return {"is_admin": user_count == 0}
    except Exception as e:
        logger.error(f"Error checking for admin user status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking admin status: {str(e)}",
        )


@router.get("/me", response_model=Dict[str, Any], tags=["users"])
async def get_user_me(request: Request, user=Depends(fastapi_users.current_user(active=True))):
    """Get current user profile information."""
    logger.debug(f"User profile requested: {user.id}")
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "is_verified": user.is_verified,
        "role": user.role,
        "created_at": user.created_at,
    }


@router.patch("/me", response_model=Dict[str, Any], tags=["users"])
async def update_user_profile(
    profile_data: UserUpdate,
    request: Request,
    user: User = Depends(current_active_user),
    user_manager: UserManager = Depends(get_user_manager),
):
    """Update the current user's profile information."""
    logger.debug(f"Profile update requested for user: {user.id}")

    # Log headers for debugging (omit sensitive info)
    auth_header = request.headers.get("Authorization", "").startswith("Bearer ")
    logger.debug(f"Auth header present: {auth_header}")

    try:
        # Update the user's profile
        updated_user = await user_manager.update(user, profile_data)

        logger.debug(f"Profile updated successfully for user: {user.id}")
        return {
            "id": str(updated_user.id),
            "email": updated_user.email,
            "full_name": updated_user.full_name,
        }
    except Exception as e:
        logger.error(f"Error updating profile for user {user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating profile: {str(e)}",
        )


class PasswordChangeRequest(BaseModel):
    """Schema for password change request."""

    current_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8)


@router.patch("/users/me/password", response_model=Dict[str, Any], tags=["users"])
async def change_user_password(
    password_data: PasswordChangeRequest,
    request: Request,
    user: User = Depends(current_active_user),
    user_manager: UserManager = Depends(get_user_manager),
):
    """Change the current user's password."""
    logger.debug(f"Password change requested for user: {user.id}")

    # Log headers for debugging (omit sensitive info)
    auth_header = request.headers.get("Authorization", "").startswith("Bearer ")
    logger.debug(f"Auth header present: {auth_header}")

    try:
        # Verify the current password
        verified = user_manager.password_helper.verify_and_update(
            password_data.current_password, user.hashed_password
        )

        if not verified[0]:
            logger.warning(f"Incorrect current password for user: {user.id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )

        # Update the password
        user.hashed_password = user_manager.password_helper.hash(password_data.new_password)
        await user.save()

        logger.debug(f"Password successfully changed for user: {user.id}")
        return {"message": "Password updated successfully"}
    except Exception as e:
        logger.error(f"Error changing password for user {user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error changing password: {str(e)}",
        )
