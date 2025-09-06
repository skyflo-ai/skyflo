import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request

from ..models.conversation import Conversation, Message, ConversationUpdate
from ..config import rate_limit_dependency
from ..services.auth import fastapi_users

logger = logging.getLogger(__name__)

router = APIRouter()


def check_conversation_authorization(
    conversation: Conversation, user, raise_on_fail: bool = True
) -> bool:
    """Check if user is authorized to access the conversation."""
    if not user:
        return True  # Allow unauthenticated access

    is_authorized = conversation.user_id == getattr(user, "id", None) or getattr(
        user, "is_superuser", False
    )

    if not is_authorized and raise_on_fail:
        raise HTTPException(status_code=403, detail="Not authorized for conversation")

    return is_authorized


async def get_conversation(conversation_id: str) -> Optional[Conversation]:
    try:
        return await Conversation.get(id=conversation_id)
    except Exception as e:
        logger.error(f"Error fetching conversation {conversation_id}: {str(e)}")
        return None


@router.post("/", dependencies=[rate_limit_dependency])
async def create_conversation(
    request: Request,
    user=Depends(fastapi_users.current_user(optional=True)),
) -> Dict[str, Any]:
    try:
        data = await request.json()
        client_conversation_id = data.get("conversation_id")

        if user:
            conversation_id = client_conversation_id
            if conversation_id:
                try:
                    conversation_id = uuid.UUID(conversation_id)
                except ValueError:
                    conversation_id = uuid.uuid4()
            else:
                conversation_id = uuid.uuid4()

            conversation = await Conversation.create(
                id=conversation_id,
                title="",
                user=user,
            )

            await Message.create(
                conversation=conversation,
                role="system",
                content="Welcome to Skyflo.ai! How can I help you with your Kubernetes infrastructure today?",
                sequence=1,
            )

            return {
                "status": "success",
                "id": str(conversation.id),
                "title": conversation.title,
                "created_at": conversation.created_at.isoformat(),
            }
        else:
            conversation_id = client_conversation_id or str(uuid.uuid4())
            return {
                "status": "success",
                "id": conversation_id,
                "title": "",
                "created_at": datetime.now().isoformat(),
            }

    except Exception as e:
        logger.exception(f"Error creating conversation: {str(e)}")
        fallback_id = str(uuid.uuid4())
        return {
            "status": "error",
            "id": client_conversation_id or fallback_id,
            "title": "New Conversation",
            "created_at": datetime.now().isoformat(),
            "error_message": str(e),
        }


@router.get("/", dependencies=[rate_limit_dependency])
async def get_conversations(
    user=Depends(fastapi_users.current_user(active=True)),
    limit: int = 20,
    cursor: Optional[str] = None,
) -> Dict[str, Any]:
    try:
        # Enforce sane limits
        if limit <= 0:
            limit = 20
        limit = min(limit, 50)

        query = Conversation.filter(user=user).order_by("-created_at")

        if cursor:
            cursor_dt: Optional[datetime] = None
            # Try ISO datetime first
            try:
                cursor_dt = datetime.fromisoformat(cursor)
            except Exception:
                cursor_dt = None

            # If not a datetime, try UUID to look up the conversation's created_at
            if cursor_dt is None:
                try:
                    cursor_uuid = uuid.UUID(cursor)
                    conv = await Conversation.get(id=cursor_uuid)
                    cursor_dt = conv.created_at if conv else None
                except Exception:
                    cursor_dt = None

            if cursor_dt is None:
                raise HTTPException(status_code=400, detail="Invalid cursor")

            query = query.filter(created_at__lt=cursor_dt)

        conversations = await query.limit(limit)

        next_cursor = (
            conversations[-1].created_at.isoformat() if len(conversations) == limit else None
        )

        return {
            "status": "success",
            "data": [
                {
                    "id": str(conversation.id),
                    "title": conversation.title,
                    "created_at": conversation.created_at.isoformat(),
                    "updated_at": conversation.updated_at.isoformat(),
                }
                for conversation in conversations
            ],
            "pagination": {
                "limit": limit,
                "next_cursor": next_cursor,
                "has_more": next_cursor is not None,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting conversations: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting conversations: {str(e)}",
        )


@router.get("/{conversation_id}", dependencies=[rate_limit_dependency])
async def check_conversation(
    conversation_id: str,
    user=Depends(fastapi_users.current_user(optional=True)),
) -> Dict[str, Any]:
    try:
        conversation = await get_conversation(conversation_id)

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        check_conversation_authorization(conversation, user)

        return {
            "status": "success",
            "exists": True,
            "id": str(conversation.id),
            "created_at": conversation.created_at.isoformat(),
            "messages": conversation.messages_json,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error checking conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error checking conversation: {str(e)}")


@router.patch("/{conversation_id}", dependencies=[rate_limit_dependency])
async def update_conversation(
    conversation_id: str,
    update_data: ConversationUpdate,
    user=Depends(fastapi_users.current_user(optional=True)),
) -> Dict[str, Any]:
    try:
        conversation = await get_conversation(conversation_id)

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        check_conversation_authorization(conversation, user)

        update_dict = update_data.model_dump(exclude_unset=True)

        if update_dict:
            await conversation.update_from_dict(update_dict)
            await conversation.save()

        return {
            "status": "success",
            "id": str(conversation.id),
            "title": conversation.title,
            "updated_at": conversation.updated_at.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error updating conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating conversation: {str(e)}")


@router.delete("/{conversation_id}", dependencies=[rate_limit_dependency])
async def delete_conversation(
    conversation_id: str,
    user=Depends(fastapi_users.current_user(optional=True)),
) -> Dict[str, Any]:
    try:
        conversation = await get_conversation(conversation_id)

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        check_conversation_authorization(conversation, user)

        await Message.filter(conversation=conversation).delete()

        await conversation.delete()

        return {
            "status": "success",
            "message": "Conversation deleted successfully",
            "id": conversation_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting conversation: {str(e)}")
