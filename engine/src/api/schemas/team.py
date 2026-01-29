from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class TeamMemberCreate(BaseModel):
    email: EmailStr
    role: str = Field(default="member", description="Role for the new user")
    password: str = Field(
        min_length=8,
        description="Initial password for the new user (minimum 8 characters)",
    )


class TeamMemberUpdate(BaseModel):
    role: str = Field(description="Updated role for the user")


class TeamMemberRead(BaseModel):
    id: str
    email: str
    name: str
    role: str
    status: str  # "active", "pending", "inactive"
    created_at: str


class TeamInvitationRead(BaseModel):
    id: str
    email: str
    role: str
    created_at: str
    expires_at: Optional[str] = None
