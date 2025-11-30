"""Conversation and Message models for chat history."""

import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime

from pydantic import BaseModel
from tortoise import fields
from tortoise.models import Model


class Conversation(Model):
    """Conversation model for tracking chat sessions."""

    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    title = fields.CharField(max_length=255, null=True)
    user = fields.ForeignKeyField("models.User", related_name="conversations")
    is_active = fields.BooleanField(default=True)
    conversation_metadata = fields.JSONField(null=True)
    messages_json = fields.JSONField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    messages = fields.ReverseRelation["Message"]

    class Meta:
        """Tortoise ORM model configuration."""

        table = "conversations"

    def __str__(self) -> str:
        """String representation of the conversation."""
        return f"<Conversation {self.id}>"


class Message(Model):
    """Message model for storing individual chat messages."""

    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    conversation = fields.ForeignKeyField("models.Conversation", related_name="messages")
    role = fields.CharField(max_length=50)
    content = fields.TextField()
    sequence = fields.IntField()
    message_metadata = fields.JSONField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        """Tortoise ORM model configuration."""

        table = "messages"

    def __str__(self) -> str:
        """String representation of the message."""
        return f"<Message {self.id} role={self.role}>"


class TokenUsageMetrics(BaseModel):
    """Captured token and latency metrics for an assistant response."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0
    cost: float = 0.0
    ttft_ms: Optional[int] = None
    ttr_ms: Optional[int] = None


class MessageCreate(BaseModel):
    """Schema for message creation."""

    role: str
    content: str
    sequence: int
    message_metadata: Optional[Dict[str, Any]] = None


class MessageRead(BaseModel):
    """Schema for reading message data."""

    id: uuid.UUID
    role: str
    content: str
    sequence: int
    message_metadata: Optional[Dict[str, Any]] = None
    token_usage: Optional[TokenUsageMetrics] = None
    created_at: datetime

    class Config:
        """Pydantic model configuration."""

        from_attributes = True


class ConversationCreate(BaseModel):
    """Schema for conversation creation."""

    title: Optional[str] = None
    conversation_metadata: Optional[Dict[str, Any]] = None


class ConversationRead(BaseModel):
    """Schema for reading conversation data."""

    id: uuid.UUID
    title: Optional[str]
    user_id: uuid.UUID
    is_active: bool
    conversation_metadata: Optional[Dict[str, Any]] = None
    messages_json: Optional[List[Dict[str, Any]]] = None
    created_at: datetime
    updated_at: datetime
    messages: Optional[List[MessageRead]] = None

    class Config:
        """Pydantic model configuration."""

        from_attributes = True


class ConversationUpdate(BaseModel):
    """Schema for updating conversation data."""

    title: Optional[str] = None
    is_active: Optional[bool] = None
    conversation_metadata: Optional[Dict[str, Any]] = None
    messages_json: Optional[List[Dict[str, Any]]] = None
