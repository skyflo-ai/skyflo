"""Authentication service using FastAPI Users."""

import uuid
from typing import Optional, Dict, Any
from fastapi import Depends, Request, HTTPException, status

from fastapi_users import FastAPIUsers
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users_tortoise import TortoiseUserDatabase
from fastapi_users.manager import BaseUserManager, UUIDIDMixin

from ..config import settings
from ..domain.models.user import User, UserCreate, UserUpdate


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    """User manager for FastAPI Users."""

    reset_password_token_secret = settings.JWT_SECRET
    verification_token_secret = settings.JWT_SECRET

    async def on_after_register(self, user: User, request: Optional[Request] = None) -> None:
        """Handle post-registration actions."""
        print(f"User {user.id} has registered.")

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ) -> None:
        """Handle post-forgot-password actions."""
        print(f"User {user.id} has forgot their password. Reset token: {token}")

    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ) -> None:
        """Handle post-verification-request actions."""
        print(f"Verification requested for user {user.id}. Verification token: {token}")

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return await User.get_or_none(email=email)

    async def get_by_id(self, id: uuid.UUID) -> Optional[User]:
        """Get user by ID."""
        return await User.get_or_none(id=id)

    async def create(
        self, user_create: UserCreate, safe: bool = True, request: Optional[Request] = None
    ) -> User:
        """Create a new user."""
        user_dict = user_create.model_dump()

        # Check if user already exists
        existing_user = await self.get_by_email(user_dict["email"])
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists",
            )

        # Check if this is the first user
        user_count = await User.all().count()
        is_first_user = user_count == 0

        password = user_dict.pop("password")
        hashed_password = self.password_helper.hash(password)

        user = await User.create(
            email=user_dict["email"],
            hashed_password=hashed_password,
            full_name=user_dict.get("full_name"),
            is_active=True,
            is_superuser=is_first_user,  # Make first user a superuser
            is_verified=is_first_user,  # Auto-verify first user
            role=(
                "admin" if is_first_user else user_dict.get("role", "member")
            ),  # Set first user as admin
        )

        return user

    async def update(self, user: User, user_update: UserUpdate) -> User:
        """Update a user."""
        update_dict = user_update.model_dump(exclude_unset=True)

        # Handle password update
        if "password" in update_dict:
            hashed_password = self.password_helper.hash(update_dict.pop("password"))
            user.hashed_password = hashed_password

        # Update other fields
        for field, value in update_dict.items():
            setattr(user, field, value)

        await user.save()
        return user

    async def get_user_dict(self, user: User) -> Dict[str, Any]:
        """Get a user as a dictionary for response."""
        teams = await user.teams.all()
        team_names = [team.name for team in teams]

        user_dict = {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "is_verified": user.is_verified,
            "role": user.role,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
            "teams": team_names,
        }
        return user_dict


async def get_user_db():
    """Get user database."""
    yield TortoiseUserDatabase(User)


async def get_user_manager(user_db: TortoiseUserDatabase = Depends(get_user_db)):
    """Get user manager."""
    yield UserManager(user_db)


# Bearer transport for token
bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")


# JWT strategy for token generation and validation
def get_jwt_strategy() -> JWTStrategy:
    """Get JWT strategy."""
    return JWTStrategy(
        secret=settings.JWT_SECRET,
        lifetime_seconds=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# JWT authentication backend
auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

# FastAPI Users instance
fastapi_users = FastAPIUsers[User, uuid.UUID](
    get_user_manager,
    [auth_backend],
)

# Current user dependencies
current_active_user = fastapi_users.current_user(active=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)
