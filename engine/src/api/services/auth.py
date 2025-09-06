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
from ..models.user import User, UserCreate, UserUpdate


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):

    reset_password_token_secret = settings.JWT_SECRET
    verification_token_secret = settings.JWT_SECRET

    async def on_after_register(self, user: User, request: Optional[Request] = None) -> None:
        print(f"User {user.id} has registered.")

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ) -> None:
        print(f"User {user.id} has forgot their password. Reset token: {token}")

    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ) -> None:
        print(f"Verification requested for user {user.id}. Verification token: {token}")

    async def get_by_email(self, email: str) -> Optional[User]:
        return await User.get_or_none(email=email)

    async def get_by_id(self, id: uuid.UUID) -> Optional[User]:
        return await User.get_or_none(id=id)

    async def create(
        self, user_create: UserCreate, safe: bool = True, request: Optional[Request] = None
    ) -> User:
        user_dict = user_create.model_dump()

        existing_user = await self.get_by_email(user_dict["email"])
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists",
            )

        user_count = await User.all().count()
        is_first_user = user_count == 0

        password = user_dict.pop("password")
        hashed_password = self.password_helper.hash(password)

        user = await User.create(
            email=user_dict["email"],
            hashed_password=hashed_password,
            full_name=user_dict.get("full_name"),
            is_active=True,
            is_superuser=is_first_user,
            is_verified=is_first_user,
            role=("admin" if is_first_user else user_dict.get("role", "member")),
        )

        return user

    async def update(self, user: User, user_update: UserUpdate) -> User:
        update_dict = user_update.model_dump(exclude_unset=True)

        if "password" in update_dict:
            hashed_password = self.password_helper.hash(update_dict.pop("password"))
            user.hashed_password = hashed_password

        for field, value in update_dict.items():
            setattr(user, field, value)

        await user.save()
        return user

    async def get_user_dict(self, user: User) -> Dict[str, Any]:
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
    yield TortoiseUserDatabase(User)


async def get_user_manager(user_db: TortoiseUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)


bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(
        secret=settings.JWT_SECRET,
        lifetime_seconds=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](
    get_user_manager,
    [auth_backend],
)

current_active_user = fastapi_users.current_user(active=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)
