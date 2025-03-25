"""Chat endpoints for processing natural language queries."""

import logging
from typing import Dict, Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from ...workflow import WorkflowManager
from ...domain.models.conversation import Conversation, Message
from ..dependencies import rate_limit_dependency
from ..endpoints.ws import socket_io_agent_event

logger = logging.getLogger(__name__)

router = APIRouter()


# Initialize with a callback that sends events to Socket.IO
async def tool_event_callback(event: Dict[str, Any]):
    """Send tool events to all clients."""
    logger.info(f"Triggering tool event callback for event in chat.py: {event}")

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
        logger.info(f"Triggering tool event callback for conversation_id: {conversation_id}")
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
    logger.info(f"Processing query: {request.query}")

    try:
        # Execute the workflow
        result = await workflow.execute_workflow(
            query=request.query,
            conversation_id=request.conversation_id,
        )

        logger.info(f"Workflow result: {result}")

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


# Additional endpoints for conversations are implemented in the WebSocket module (ws.py)
# - POST /ws/conversations - Create a new conversation
# - GET /ws/conversations - List conversations
