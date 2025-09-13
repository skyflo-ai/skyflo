"""Integration model for external provider configs (e.g., Jenkins)."""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel
from tortoise import fields
from tortoise.models import Model


class Integration(Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid4)

    user = fields.ForeignKeyField("models.User", related_name="integrations")

    provider = fields.CharField(max_length=50, unique=True)
    name = fields.CharField(max_length=100, null=True)

    metadata = fields.JSONField(null=True)

    credentials_ref = fields.CharField(max_length=255)

    status = fields.CharField(max_length=20, default="active")

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "integrations"
        unique_together = ("provider",)


class IntegrationCreate(BaseModel):
    provider: str
    name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    credentials: Dict[str, str]


class IntegrationRead(BaseModel):
    id: uuid.UUID
    provider: str
    name: Optional[str]
    metadata: Optional[Dict[str, Any]] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class IntegrationUpdate(BaseModel):
    name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    credentials: Optional[Dict[str, str]] = None
    status: Optional[str] = None
