"""Team related schema definitions."""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class TeamMemberCreate(BaseModel):
    """Schema for creating a team member invitation."""

    email: EmailStr
    role: str = Field(default="member", description="Role for the new user")
    password: str = Field(description="Initial password for the new user")


class TeamMemberUpdate(BaseModel):
    """Schema for updating a team member."""

    role: str = Field(description="Updated role for the user")


class TeamMemberRead(BaseModel):
    """Schema for reading team member information."""

    id: str
    email: str
    name: str
    role: str
    status: str  # "active", "pending", "inactive"
    created_at: str


class TeamInvitationRead(BaseModel):
    """Schema for reading invitation information."""

    id: str
    email: str
    role: str
    created_at: str
    expires_at: Optional[str] = None
