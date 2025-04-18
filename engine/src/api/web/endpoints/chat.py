"""Chat endpoints for processing natural language queries."""

import logging
import uuid
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel, Field

from ...workflow import WorkflowManager
from ...domain.models.conversation import Conversation, Message
from ..dependencies import rate_limit_dependency
from ..endpoints.ws import socket_io_agent_event
from ...services.auth import fastapi_users

logger = logging.getLogger(__name__)

router = APIRouter()


# Initialize with a callback that sends events to Socket.IO
async def tool_event_callback(event: Dict[str, Any]):
    """Send tool events to all clients."""
    logger.debug(f"Triggering tool event callback for event in chat.py: {event}")

    # Check for conversation_id in both root level and data field
    conversation_id = None

    # First check in data field since that's where tool_call_completed events have it
    if isinstance(event.get("data"), dict) and "conversation_id" in event["data"]:
        conversation_id = event["data"]["conversation_id"]
    # Then check in details field for workflow events
    elif isinstance(event.get("details"), dict) and "conversation_id" in event["details"]:
        conversation_id = event["details"]["conversation_id"]
    # Finally check root level
    elif "conversation_id" in event:
        conversation_id = event["conversation_id"]

    if conversation_id:
        logger.debug(f"Triggering tool event callback for conversation_id: {conversation_id}")
        room = f"conversation:{conversation_id}"
        await socket_io_agent_event(room, event)
    else:
        logger.warning("No conversation_id found in event")


# Initialize workflow manager with the callback
workflow_manager = WorkflowManager(event_callback=tool_event_callback)


async def get_workflow_manager() -> WorkflowManager:
    """Get the workflow manager as a FastAPI dependency."""
    return workflow_manager


class QueryRequest(BaseModel):
    """Request model for processing a natural language query."""

    query: str = Field(..., description="The natural language query to process")
    conversation_id: Optional[str] = Field(None, description="Optional conversation ID for context")


class QueryResponse(BaseModel):
    """Response model for query processing results."""

    status: str = Field(..., description="Status of the query processing")
    result: Dict[str, Any] = Field(..., description="Results of the query processing")
    duration: float = Field(..., description="Duration of query processing in seconds")
    error: Optional[str] = Field(None, description="Error message if status is 'error'")


@router.post("/query", response_model=QueryResponse, dependencies=[rate_limit_dependency])
async def process_query(
    request: QueryRequest,
    background_tasks: BackgroundTasks,
    workflow: WorkflowManager = Depends(get_workflow_manager),
) -> Dict[str, Any]:
    """Process a natural language query and return results.

    This endpoint uses the workflow manager to execute the query through the
    Engine component's workflow system.
    """
    logger.debug(f"Processing query: {request.query}")

    try:
        # Execute the workflow
        result = await workflow.execute_workflow(
            query=request.query,
            conversation_id=request.conversation_id,
        )

        logger.debug(f"Workflow result: {result}")

        # Store query and result in the database if conversation_id is provided
        if request.conversation_id:
            try:
                # Get the conversation
                conversation = await Conversation.get(id=UUID(request.conversation_id))

                # Get next sequence number
                next_sequence = await Message.filter(conversation_id=conversation.id).count() + 1

                # Store the user query
                await Message.create(
                    conversation=conversation,
                    role="user",
                    content=request.query,
                    sequence=next_sequence,
                )

                # Store the assistant response
                await Message.create(
                    conversation=conversation,
                    role="assistant",
                    content=result.get("response", ""),
                    sequence=next_sequence + 1,
                    message_metadata=result,
                )
            except Exception as db_error:
                logger.error(f"Error storing conversation: {str(db_error)}")
                # Continue even if storing fails

        return {
            "status": result.get("status", "success"),
            "result": result,
            "duration": result.get("duration", 0.0),
            "error": result.get("error"),
        }

    except Exception as e:
        logger.exception(f"Error processing query: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}",
        )


@router.post("/query/reset", dependencies=[rate_limit_dependency])
async def reset_workflow_state(
    workflow: WorkflowManager = Depends(get_workflow_manager),
) -> Dict[str, Any]:
    """Reset the workflow state to start fresh."""
    workflow.reset_state()
    return {"status": "success", "message": "Workflow state reset successfully"}


@router.post("/conversations")
async def create_conversation(
    request: Request,
    user=Depends(fastapi_users.current_user(optional=True)),
) -> Dict[str, Any]:
    """Create a new conversation with the provided ID or generate a new one."""
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
                title=data.get("title", f"New Conversation {uuid.uuid4().hex[:8]}"),
                user=user,
            )

            await Message.create(
                conversation=conversation,
                role="system",
                content="Welcome to Skyflo.ai! How can I help you with your Kubernetes infrastructure today?",
                sequence=1,
            )

            logger.debug(f"Created new conversation {conversation.id} for user {user.id}")
            return {
                "status": "success",
                "id": str(conversation.id),
                "title": conversation.title,
                "created_at": conversation.created_at.isoformat(),
            }
        else:
            conversation_id = client_conversation_id or str(uuid.uuid4())
            logger.debug(
                f"Using client-provided conversation ID {conversation_id} for unauthenticated user"
            )
            return {
                "status": "success",
                "id": conversation_id,
                "title": data.get("title", "New Conversation"),
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


@router.get("/conversations")
async def get_conversations(
    user=Depends(fastapi_users.current_user(active=True)),
) -> Dict[str, Any]:
    """Get all conversations for the current user."""
    try:
        conversations = await Conversation.filter(user=user).order_by("-created_at")

        logger.debug(f"Retrieved {len(conversations)} conversations for user {user.id}")
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
        }

    except Exception as e:
        logger.exception(f"Error getting conversations: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting conversations: {str(e)}",
        )


async def get_conversation(conversation_id: str) -> Optional[Conversation]:
    """Helper function to get a conversation by ID."""
    try:
        return await Conversation.get(id=conversation_id)
    except Exception as e:
        logger.error(f"Error fetching conversation {conversation_id}: {str(e)}")
        return None


@router.get("/conversations/{conversation_id}")
async def check_conversation(
    conversation_id: str,
    user=Depends(fastapi_users.current_user(optional=True)),
) -> Dict[str, Any]:
    """Check if a conversation exists."""
    try:
        conversation = await get_conversation(conversation_id)

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        if user and conversation.user_id != user.id and not user.is_superuser:
            raise HTTPException(
                status_code=403, detail="Not authorized to access this conversation"
            )

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


@router.patch("/conversations/{conversation_id}/messages")
async def update_messages_in_conversation(
    conversation_id: str,
    request: Request,
    user=Depends(fastapi_users.current_user(active=True)),
) -> Dict[str, Any]:
    """Update messages in a conversation."""
    try:
        conversation = await get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        if conversation.user_id != user.id and not user.is_superuser:
            raise HTTPException(
                status_code=403, detail="Not authorized to update this conversation"
            )

        data = await request.json()
        messages = data.get("messages")

        if not messages or not isinstance(messages, list):
            raise HTTPException(status_code=400, detail="Request must include 'messages' as a list")

        await conversation.update_from_dict({"messages_json": messages}).save()

        return {
            "status": "success",
            "conversation_id": str(conversation.id),
            "messages": messages,
            "updated_at": conversation.updated_at.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error updating conversation messages: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error updating conversation messages: {str(e)}"
        )
