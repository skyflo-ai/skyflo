"""User model definition."""

import uuid
from typing import Optional
from datetime import datetime

from fastapi_users.schemas import BaseUser, BaseUserCreate, BaseUserUpdate
from tortoise import fields, models


class User(models.Model):
    """User model for authentication and profile information."""

    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    email = fields.CharField(max_length=255, unique=True, index=True)
    hashed_password = fields.CharField(max_length=255)
    full_name = fields.CharField(max_length=255, null=True)
    is_active = fields.BooleanField(default=True)
    is_superuser = fields.BooleanField(default=False)
    is_verified = fields.BooleanField(default=False)
    role = fields.CharField(max_length=20, default="member")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    conversations = fields.ReverseRelation["Conversation"]

    class Meta:
        """Tortoise ORM model configuration."""

        table = "users"

    def __str__(self) -> str:
        """String representation of the user."""
        return f"<User {self.email}>"


class UserCreate(BaseUserCreate):
    """Schema for user creation."""

    full_name: Optional[str] = None
    role: Optional[str] = "member"


class UserRead(BaseUser[uuid.UUID]):
    """Schema for reading user data."""

    full_name: Optional[str] = None
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseUserUpdate):
    """Schema for updating user data."""

    full_name: Optional[str] = None
    role: Optional[str] = None


class UserDB(BaseUser[uuid.UUID]):
    """Schema for user in database with hashed password."""

    hashed_password: str
    full_name: Optional[str] = None
    role: str = "member"
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
