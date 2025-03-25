"""Domain models package."""

# Tortoise ORM models
from .user import User
from .conversation import Conversation, Message

# Pydantic schemas
from .user import UserCreate, UserRead, UserUpdate, UserDB
from .conversation import (
    ConversationCreate,
    ConversationRead,
    ConversationUpdate,
    MessageCreate,
    MessageRead,
)

__all__ = [
    # Tortoise ORM models
    "User",
    "Conversation",
    "Message",
    # Pydantic schemas
    "UserCreate",
    "UserRead",
    "UserUpdate",
    "UserDB",
    "ConversationCreate",
    "ConversationRead",
    "ConversationUpdate",
    "MessageCreate",
    "MessageRead",
]
