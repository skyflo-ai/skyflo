import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..config import rate_limit_dependency, settings
from ..models.user import User, UserCreate, UserRead, UserUpdate
from ..services.auth import (
    UserManager,
    auth_backend,
    create_refresh_token,
    current_active_user,
    fastapi_users,
    get_user_manager,
    get_valid_refresh_token,
    issue_access_token,
    revoke_refresh_token,
    rotate_refresh_token,
)

logger = logging.getLogger(__name__)
router = APIRouter()

ACCESS_TOKEN_COOKIE_NAME = "auth_token"
REFRESH_TOKEN_COOKIE_NAME = "refresh_token"


def _apply_auth_cookies(response: JSONResponse, access_token: str, refresh_token: str) -> None:
    secure_cookie = not settings.DEBUG
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=secure_cookie,
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=secure_cookie,
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        samesite="lax",
        path="/",
    )


router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/jwt",
    tags=["auth"],
)

router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/register",
    tags=["auth"],
)

router.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/verify",
    tags=["auth"],
)

router.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/reset-password",
    tags=["auth"],
)

router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)


@router.get(
    "/is_admin_user",
    response_model=Dict[str, bool],
    tags=["auth"],
    dependencies=[rate_limit_dependency],
)
async def is_admin_user():
    try:
        user_count = await User.all().count()
        return {"is_admin": user_count == 0}
    except Exception as e:
        logger.error(f"Error checking for admin user status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error checking admin status",
        ) from e


@router.get(
    "/me", response_model=Dict[str, Any], tags=["users"], dependencies=[rate_limit_dependency]
)
async def get_user_me(user: User = Depends(fastapi_users.current_user(active=True))):
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


@router.patch(
    "/me", response_model=Dict[str, Any], tags=["users"], dependencies=[rate_limit_dependency]
)
async def update_user_profile(
    profile_data: UserUpdate,
    user: User = Depends(current_active_user),
    user_manager: UserManager = Depends(get_user_manager),
):
    try:
        updated_user = await user_manager.update(user, profile_data)

        return {
            "id": str(updated_user.id),
            "email": updated_user.email,
            "full_name": updated_user.full_name,
        }
    except Exception as e:
        logger.error(f"Error updating profile for user {user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating profile",
        ) from e


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8)


@router.patch(
    "/users/me/password",
    response_model=Dict[str, Any],
    tags=["users"],
    dependencies=[rate_limit_dependency],
)
async def change_user_password(
    password_data: PasswordChangeRequest,
    user: User = Depends(current_active_user),
    user_manager: UserManager = Depends(get_user_manager),
):
    try:
        verified = user_manager.password_helper.verify_and_update(
            password_data.current_password, user.hashed_password
        )

        if not verified[0]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )

        user.hashed_password = user_manager.password_helper.hash(password_data.new_password)
        await user.save()

        return {"message": "Password updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing password for user {user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error changing password",
        ) from e


@router.post(
    "/refresh/issue",
    response_model=Dict[str, Any],
    tags=["auth"],
    dependencies=[rate_limit_dependency],
)
async def issue_refresh_token(user: User = Depends(current_active_user)):
    refresh_token = await create_refresh_token(user)
    return {
        "refresh_token": refresh_token,
        "expires_in": settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    }


@router.post(
    "/refresh",
    response_model=Dict[str, Any],
    tags=["auth"],
    dependencies=[rate_limit_dependency],
)
async def refresh_access_token(
    request: Request, user_manager: UserManager = Depends(get_user_manager)
):
    refresh_token = request.cookies.get(REFRESH_TOKEN_COOKIE_NAME)
    if not refresh_token:
        response = JSONResponse(
            {"detail": "Refresh token missing"},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
        response.delete_cookie(ACCESS_TOKEN_COOKIE_NAME, path="/")
        response.delete_cookie(REFRESH_TOKEN_COOKIE_NAME, path="/")
        return response

    stored_token = await get_valid_refresh_token(refresh_token)
    if not stored_token:
        response = JSONResponse(
            {"detail": "Refresh token invalid"},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
        response.delete_cookie(ACCESS_TOKEN_COOKIE_NAME, path="/")
        response.delete_cookie(REFRESH_TOKEN_COOKIE_NAME, path="/")
        return response

    user = stored_token.user
    access_token = await issue_access_token(user)
    new_refresh_token = await rotate_refresh_token(stored_token)
    user_dict = await user_manager.get_user_dict(user)

    response = JSONResponse(
        {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user_dict,
        }
    )
    _apply_auth_cookies(response, access_token, new_refresh_token)
    return response


@router.post(
    "/logout",
    response_model=Dict[str, Any],
    tags=["auth"],
    dependencies=[rate_limit_dependency],
)
async def logout(request: Request):
    refresh_token = request.cookies.get(REFRESH_TOKEN_COOKIE_NAME)
    if refresh_token:
        await revoke_refresh_token(refresh_token)

    response = JSONResponse({"success": True})
    response.delete_cookie(ACCESS_TOKEN_COOKIE_NAME, path="/")
    response.delete_cookie(REFRESH_TOKEN_COOKIE_NAME, path="/")
    return response
