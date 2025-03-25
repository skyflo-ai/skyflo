"""Socket.IO endpoints for real-time chat."""

import json
import logging
import uuid
from typing import Dict, Any, List, Optional, Callable, Awaitable
import asyncio
from datetime import datetime

# Replace WebSocket imports with Socket.IO
from fastapi import APIRouter, Depends, HTTPException, Request
import socketio
from broadcaster import Broadcast
from tortoise.expressions import Q
import time

from ...domain.models.user import User
from ...domain.models.conversation import Conversation, Message
from ...services.auth import fastapi_users
from ...workflow import WorkflowManager
from ...config import settings
from ...services.mcp_client import register_global_callback
from ...workflow.agents.executor.main import handle_tool_call_approval, handle_tool_call_rejection

# Configure more detailed logging for the Socket.IO module
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, settings.LOG_LEVEL))

router = APIRouter()

# Initialize Socket.IO server
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=True,
    ping_timeout=60,  # Increase timeout (in seconds)
    ping_interval=25,  # Set ping interval (in seconds)
    max_http_buffer_size=10000000,  # Increase buffer size for large messages
    always_connect=True,  # Always accept the connection and do auth later
)
sio_app = socketio.ASGIApp(sio)

# Initialize broadcaster for pub/sub
broadcast = Broadcast(settings.REDIS_URL)

# Keep track of active connections
active_connections: Dict[str, List[str]] = {}


async def socket_event_callback(event: Dict[str, Any]):
    """Callback for Socket.IO events."""
    # Get room from conversation_id if available
    room = None
    if "conversation_id" in event:
        room = f"conversation:{event['conversation_id']}"
    elif (
        "details" in event
        and isinstance(event["details"], dict)
        and "conversation_id" in event["details"]
    ):
        room = f"conversation:{event['details']['conversation_id']}"

    if room:
        await socket_io_agent_event(room, event)
    else:
        logger.warning(f"No room found for event: {event.get('type', 'unknown')}")


# Register the callback globally
register_global_callback(socket_event_callback)
logger.info("Registered socket_event_callback globally")

# Initialize workflow manager with event callback
workflow_manager = WorkflowManager(event_callback=socket_event_callback)


async def get_workflow_manager() -> WorkflowManager:
    """Get the workflow manager as a FastAPI dependency."""
    return workflow_manager


@router.on_event("startup")
async def startup_event():
    """Start broadcaster on application startup."""
    await broadcast.connect()
    logger.info("Socket.IO broadcaster connected")


@router.on_event("shutdown")
async def shutdown_event():
    """Close broadcaster on application shutdown."""
    await broadcast.disconnect()
    logger.info("Socket.IO broadcaster disconnected")


async def get_conversation(conversation_id: str) -> Optional[Conversation]:
    """Get a conversation by ID."""
    try:
        return await Conversation.get(id=conversation_id)
    except Exception as e:
        logger.error(f"Error fetching conversation {conversation_id}: {str(e)}")
        return None


# Add a ping handler to keep connections alive
@sio.on("ping")
async def handle_ping(sid, data=None):
    """Handle client ping to keep connection alive."""
    try:
        logger.debug(f"Received ping from client {sid}")
        await sio.emit("pong", {"timestamp": time.time()}, room=sid)
    except Exception as e:
        logger.exception(f"Error in ping handler: {str(e)}")


@sio.on("tool_call_approved")
async def handle_tool_call_approval_message(sid, data=None):
    """Handle tool call approval event."""
    logger.info(f"Received tool call approval from client {sid}")
    logger.info(f"Tool call approval data: {data}")
    await handle_tool_call_approval(data["step_id"])


@sio.on("tool_call_rejected")
async def handle_tool_call_rejection_message(sid, data=None):
    """Handle tool call rejection event."""
    logger.info(f"Received tool call rejection from client {sid}")
    logger.info(f"Tool call rejection data: {data}")
    handle_tool_call_rejection(data["step_id"])


@sio.event
async def connect(sid, environ, auth=None):
    """Handle Socket.IO connection event."""
    logger.info(f"Socket.IO client connected: {sid}")

    # Log connection details for debugging
    logger.debug(f"Connection request details for {sid}:")
    logger.debug(f"  - Environment variables: {environ}")
    logger.debug(f"  - Headers: {environ.get('HTTP_HEADERS', {})}")
    logger.debug(f"  - Request path: {environ.get('PATH_INFO', '')}")
    logger.debug(f"  - Remote address: {environ.get('REMOTE_ADDR', 'unknown')}")
    logger.debug(f"  - Protocol: {environ.get('wsgi.url_scheme', 'unknown')}")
    logger.debug(
        f"  - Connection count before connect: {sum(len(clients) for clients in active_connections.values())}"
    )

    # Get conversation ID from query parameters
    try:
        query = environ.get("QUERY_STRING", "")
        logger.debug(f"  - Query string: {query}")

        params = {k: v for k, v in [p.split("=") for p in query.split("&") if "=" in p]}
        logger.debug(f"  - Parsed params: {params}")

        conversation_id = params.get("conversation_id")
        auth_token = params.get("token")

        logger.debug(f"  - Conversation ID from params: {conversation_id}")
        logger.debug(f"  - Auth token present: {'Yes' if auth_token else 'No'}")

        if not conversation_id:
            logger.error("No conversation_id provided in connection request")
            await sio.emit(
                "error",
                {
                    "type": "error",
                    "data": {
                        "message": "No conversation_id provided. This is required for proper Socket.IO connection."
                    },
                },
                room=sid,
            )
            return False

        logger.info(f"Client {sid} connecting to conversation {conversation_id}")

        # Verify the auth token if provided
        user = None
        if auth_token:
            try:
                # Import necessary modules for token verification
                from ...services.auth import fastapi_users, auth_backend
                from fastapi_users.jwt import decode_jwt

                # Verify the token
                logger.info(f"Verifying auth token for client {sid}")
                decoded_token = decode_jwt(
                    auth_token,
                    settings.JWT_SECRET,
                    audience="fastapi-users:auth",  # Add the required audience parameter
                )

                # Get the user ID from the token
                user_id = decoded_token.get("sub")
                if user_id:
                    # Update to use the correct method to get user
                    try:
                        # Import the correct dependencies for user authentication
                        from ...services.auth import current_active_user

                        # For WebSocket connections, we can't use dependency injection directly
                        # So we'll use a simpler approach by directly importing the User model
                        from ...domain.models.user import User

                        # Convert the user ID to a UUID object and find the user in the database
                        user_uuid = uuid.UUID(user_id)
                        user = await User.filter(id=user_uuid).first()

                        if user:
                            logger.info(f"Authenticated user {user.email} for client {sid}")
                        else:
                            logger.warning(f"User with ID {user_id} not found for client {sid}")
                    except Exception as user_error:
                        logger.warning(
                            f"Failed to retrieve user for client {sid}: {str(user_error)}"
                        )
                        # Continue without user authentication
                else:
                    logger.warning(f"No user ID found in token for client {sid}")
            except Exception as token_error:
                logger.warning(f"Invalid auth token for client {sid}: {str(token_error)}")
                # We'll still allow connection but log the authentication failure
        else:
            logger.warning(f"No auth token provided for client {sid}")

        # Add connection to active connections for this conversation
        if conversation_id not in active_connections:
            active_connections[conversation_id] = []
        active_connections[conversation_id].append(sid)

        # Join the Socket.IO room for this conversation
        await sio.enter_room(sid, f"conversation:{conversation_id}")

        # Send initial connection status event
        await sio.emit(
            "connection_status",
            {
                "type": "connection_status",
                "data": {
                    "status": "connecting",
                    "message": "Establishing secure WebSocket connection...",
                    "conversation_id": conversation_id,
                    "timestamp": time.time(),
                    "sid": sid,
                },
            },
            room=sid,
        )

        # Wait a brief moment before sending history to prevent race conditions
        await asyncio.sleep(0.05)

        # Get existing conversation
        conversation = await get_conversation(conversation_id)

        # Only send messages if conversation exists and user has access or no user authentication required
        if conversation:
            # Check if user has access to this conversation (if authenticated)
            user_access = True
            if user and conversation.user_id != user.id and not user.is_superuser:
                logger.warning(
                    f"User {user.email} does not have access to conversation {conversation_id}"
                )
                user_access = False
                # We allow the connection but won't send history
                await sio.emit(
                    "connected",
                    {
                        "type": "connected",
                        "data": {
                            "conversation_id": conversation_id,
                            "authenticated": True,
                            "authorized": False,
                            "message": "Connected, but you don't have permission to view this conversation",
                            "timestamp": time.time(),
                        },
                    },
                    room=sid,
                )
                return True

            # Send existing messages to the client
            messages = await conversation.messages.all().order_by("sequence")
            logger.info(
                f"Sending {len(messages)} existing messages to client for conversation {conversation_id}"
            )

            # First notify client about history loading
            if len(messages) > 0:
                await sio.emit(
                    "history_loading",
                    {
                        "type": "history_loading",
                        "data": {
                            "message": f"Loading conversation history ({len(messages)} messages)...",
                            "count": len(messages),
                            "timestamp": time.time(),
                        },
                    },
                    room=sid,
                )

            for index, message in enumerate(messages):
                message_data = {
                    "type": "message",
                    "data": {
                        "id": str(message.id),
                        "role": message.role,
                        "content": message.content,
                        "sequence": message.sequence,
                        "created_at": message.created_at.isoformat(),
                        "progress": f"{index + 1}/{len(messages)}",  # Add progress information
                    },
                }
                logger.debug(f"Sending message {index+1}/{len(messages)} to client")
                await sio.emit("message", message_data, room=sid)
                # Add a small delay between messages for client processing
                if (index + 1) % 5 == 0 and index + 1 < len(messages):
                    await asyncio.sleep(0.01)  # Brief delay every 5 messages

            # Notify client that history is loaded
            if len(messages) > 0:
                await sio.emit(
                    "history_loaded",
                    {
                        "type": "history_loaded",
                        "data": {
                            "message": "Conversation history loaded successfully",
                            "count": len(messages),
                            "timestamp": time.time(),
                        },
                    },
                    room=sid,
                )

        # Wait a brief moment before finalizing connection to prevent race conditions
        await asyncio.sleep(0.05)

        # Send connected confirmation
        await sio.emit(
            "connected",
            {
                "type": "connected",
                "data": {
                    "conversation_id": conversation_id,
                    "authenticated": user is not None,
                    "authorized": True,
                    "message": "WebSocket connection established successfully",
                    "timestamp": time.time(),
                    "connection_id": sid,
                },
            },
            room=sid,
        )

        # Setup regular ping to keep connection alive
        # No need for manual pings - Socket.IO handles this automatically

        return True
    except Exception as e:
        logger.exception(f"Error during Socket.IO connection: {str(e)}")
        await sio.emit(
            "error",
            {
                "type": "error",
                "data": {
                    "message": f"Connection error: {str(e)}",
                    "timestamp": time.time(),
                },
            },
            room=sid,
        )
        return False


@sio.event
async def disconnect(sid):
    """Handle Socket.IO disconnection event."""
    logger.info(f"Socket.IO client disconnected: {sid}")

    # Log more detailed debug information about the disconnect event
    client_rooms = sio.rooms(sid)
    client_conversations = [room for room in client_rooms if room.startswith("conversation:")]

    # Properly await the get_session coroutine
    try:
        client_data = await sio.get_session(sid)
    except Exception as e:
        logger.warning(f"Error getting session data for {sid}: {str(e)}")
        client_data = None

    logger.debug(f"Disconnection details for client {sid}:")
    logger.debug(f"  - Rooms: {client_rooms}")
    logger.debug(f"  - Conversations: {client_conversations}")
    logger.debug(f"  - Session data: {client_data}")
    logger.debug(
        f"  - Connection count before disconnect: {sum(len(clients) for clients in active_connections.values())}"
    )

    # Remove client from all conversation rooms
    disconnected_from = []
    for conversation_id, clients in list(active_connections.items()):
        if sid in clients:
            clients.remove(sid)
            disconnected_from.append(conversation_id)
            if not clients:
                del active_connections[conversation_id]
            logger.info(f"Removed client {sid} from conversation {conversation_id}")

    logger.debug(f"Client {sid} disconnected from conversations: {disconnected_from}")
    logger.debug(
        f"Connection count after disconnect: {sum(len(clients) for clients in active_connections.values())}"
    )
    logger.debug(f"Active connections remaining: {active_connections}")


@sio.event
async def message(sid, data):
    """Handle Socket.IO message event."""
    try:
        logger.info(f"Received client message from {sid}: {data}")

        # Get conversation ID from rooms the client is in
        client_rooms = sio.rooms(sid)
        conversation_rooms = [room for room in client_rooms if room.startswith("conversation:")]

        if not conversation_rooms:
            logger.error(f"Client {sid} not in any conversation room")
            await sio.emit(
                "error",
                {
                    "type": "error",
                    "data": {
                        "message": "Not connected to any conversation. Please refresh and try again.",
                        "timestamp": time.time(),
                    },
                },
                room=sid,
            )
            return

        # Get the conversation ID from the room name
        room_name = conversation_rooms[0]
        conversation_id = room_name.replace("conversation:", "")

        if data.get("type") == "message":
            # Send immediate acknowledgment of message receipt
            await sio.emit(
                "message_received",
                {
                    "type": "message_received",
                    "data": {
                        "message": "Your message has been received and is being processed",
                        "timestamp": time.time(),
                        "query_id": str(uuid.uuid4()),  # Generate unique ID for this query
                    },
                },
                room=room_name,
            )

            # Process message from client
            query = data.get("data", {}).get("content")
            if not query:
                logger.error(f"Received empty message from client {sid}")
                await sio.emit(
                    "error",
                    {
                        "type": "error",
                        "data": {
                            "message": "Empty message received. Please provide a query.",
                            "timestamp": time.time(),
                        },
                    },
                    room=room_name,
                )
                return

            logger.info(f"Processing user query: {query[:100]}...")

            # Store user message
            conversation = await get_conversation(conversation_id)
            if conversation:
                # Find the next sequence number
                next_sequence = await Message.filter(conversation=conversation).count() + 1

                # Store user message
                user_message = await Message.create(
                    conversation=conversation,
                    role="user",
                    content=query,
                    sequence=next_sequence,
                )

                # Emit message created event
                message_created_event = {
                    "type": "message_created",
                    "data": {
                        "id": str(user_message.id),
                        "role": "user",
                        "content": query,
                        "sequence": next_sequence,
                        "created_at": user_message.created_at.isoformat(),
                        "timestamp": time.time(),
                    },
                }
                logger.debug(f"Emitting message_created event: {message_created_event}")
                await sio.emit("message_created", message_created_event, room=room_name)

                # Signal workflow start - IMPROVED EVENT
                workflow_start_event = {
                    "type": "workflow_start",
                    "data": {
                        "timestamp": time.time(),
                        "message": "Starting multi-agent workflow execution",
                        "progress": 0.05,
                        "phase": "initialization",
                    },
                }
                logger.debug(f"Emitting workflow_start event: {workflow_start_event}")
                await sio.emit("workflow_start", workflow_start_event, room=room_name)

                # Signal planning phase start - IMPROVED EVENT
                planner_start_event = {
                    "type": "planner_start",
                    "data": {
                        "timestamp": time.time(),
                        "message": "Starting planning phase to analyze your request",
                        "phase": "planning",
                        "progress": 0.1,
                        "agent": "planner",
                    },
                }
                logger.debug(f"Emitting planner_start event: {planner_start_event}")
                await sio.emit("planner_start", planner_start_event, room=room_name)

                # Create real-time event callback function
                async def event_callback(event: Dict[str, Any]):
                    """Real-time event callback that immediately forwards events to WebSocket clients."""
                    try:
                        # Ensure the event has the basic required structure
                        if not isinstance(event, dict) or "type" not in event:
                            print(f"Invalid event format received: {event}")
                            logger.warning(f"Invalid event format received")
                            return

                        # Get the room from the conversation ID
                        conversation_id = event.get("conversation_id", None)
                        room = f"conversation:{conversation_id}" if conversation_id else None

                        # If no specific conversation, try to get it from the current context
                        if not room:
                            # Get it from the details if available
                            details = event.get("details", {})
                            if isinstance(details, dict) and "conversation_id" in details:
                                room = f"conversation:{details['conversation_id']}"

                            # If still no room, use the current conversation ID from the context
                            if not room:
                                room = room_name  # Use current conversation room from outer scope
                                logger.info(f"Using current room for event: {room}")

                        # Add timestamp if not present
                        if "data" not in event:
                            event["data"] = {}

                        if "timestamp" not in event["data"]:
                            event["data"]["timestamp"] = time.time()

                        # Log the event being emitted
                        event_type = event["type"]
                        logger.debug(f"Emitting {event_type} event to room {room}")

                        # Immediately yield control back to the event loop to ensure events are sent promptly
                        await asyncio.sleep(0)

                        # Handle special event types
                        if event_type == "plan_generated":
                            # The plan was just generated - send it to the client
                            logger.info(f"Sending generated plan to client")

                            # Extract the plan from the event
                            plan = event.get("details", {}).get("plan", {})

                            # Create a specialized event specifically for the plan data
                            plan_event = {
                                "type": "plan",
                                "data": {
                                    "plan": plan,
                                    "timestamp": time.time(),
                                    "message": "Execution plan generated",
                                    "agent": "planner",
                                    "phase": "planning",
                                },
                            }

                            # Send the plan to the client
                            await sio.emit("plan", plan_event, room=room)
                            # Small delay to ensure client processing
                            await asyncio.sleep(0.01)

                        elif event_type in [
                            "step_about_to_execute",
                            "step_executing",
                            "step_complete",
                            "step_failed",
                            "approval_required",
                        ]:
                            # Step execution state update - send step update
                            logger.info(f"Sending step update: {event_type}")

                            # Extract details
                            details = event.get("details", {})
                            step_id = details.get("step_id", "unknown")
                            status = details.get("status", "unknown")

                            # Create a step update event
                            step_event = {
                                "type": "step_update",
                                "data": {
                                    "step_id": step_id,
                                    "status": status,
                                    "tool": details.get("tool", "unknown"),
                                    "action": details.get("action", "unknown"),
                                    "timestamp": time.time(),
                                    "message": event.get("message", f"Step {step_id} {status}"),
                                    "agent": "executor",
                                    "phase": "executing",
                                    "approval_required": details.get("approval_required", False),
                                    "parameters": details.get("parameters", {}),
                                },
                            }

                            # Add output if this is a completed step
                            if status == "completed" and "output" in details:
                                step_event["data"]["output"] = details["output"]

                            # Add error if this is a failed step
                            if status == "failed" and "error" in details:
                                step_event["data"]["error"] = details["error"]

                            # Send the step update to the client
                            await sio.emit("step_update", step_event, room=room)
                            # Small delay to ensure client processing
                            await asyncio.sleep(0.01)

                        elif event_type in [
                            "verification_criteria_list",
                            "criterion_checking",
                            "criterion_result",
                            "verification_complete",
                        ]:
                            # Verification events - send verification update
                            logger.info(f"Sending verification update: {event_type}")

                            # Create verification event
                            verification_event = {
                                "type": event_type,
                                "data": {
                                    "message": event.get("message", "Verification update"),
                                    "timestamp": time.time(),
                                    "agent": "verifier",
                                    "phase": "verifying",
                                    "details": event.get("details", {}),
                                },
                            }

                            # Send the verification update to the client
                            await sio.emit(event_type, verification_event, room=room)
                            # Small delay to ensure client processing
                            await asyncio.sleep(0.01)

                        # Always emit the original event
                        await sio.emit(event_type, event, room=room)
                        # Small delay to ensure client processing
                        await asyncio.sleep(0.01)

                        # For better UI responsiveness, also emit a generic agent_update event
                        if event_type not in ["message", "error", "connected"]:
                            # Extract phase and progress info when available
                            phase = event.get("phase", "processing")
                            if "agent" in event:
                                agent_type = event["agent"].lower()
                                if "planner" in agent_type:
                                    phase = "planning"
                                elif "executor" in agent_type:
                                    phase = "executing"
                                elif "verifier" in agent_type:
                                    phase = "verifying"
                                elif "response" in agent_type:
                                    phase = "responding"

                            progress = event.get("data", {}).get("progress", None)

                            agent_update = {
                                "type": "agent_update",
                                "data": {
                                    "title": event.get("message", "Processing request"),
                                    "description": event.get("data", {}).get(
                                        "message", "Working on your request..."
                                    ),
                                    "agent_type": event.get("agent", "system"),
                                    "phase": phase,
                                    "timestamp": event.get("data", {}).get(
                                        "timestamp", time.time()
                                    ),
                                },
                            }

                            # Add progress info if available
                            if progress is not None:
                                agent_update["data"]["progress"] = progress

                            # Add completion status for *_complete events
                            if event_type.endswith("_complete"):
                                agent_update["data"]["isCompleted"] = True

                            logger.debug(f"Emitting agent_update for {event_type}")
                            await sio.emit("agent_update", agent_update, room=room)
                    except Exception as e:
                        logger.exception(f"Error in event_callback: {str(e)}")

                # Register this callback globally
                register_global_callback(event_callback)
                logger.info(
                    f"Registered per-conversation event_callback globally for conversation {conversation_id}"
                )

                # Execute workflow with real-time event callback
                try:
                    logger.info(f"Executing workflow for query: {query[:100]}...")

                    # Execute workflow - this now returns immediately with workflow running in background
                    result = await workflow_manager.execute_workflow(
                        query=query,
                        conversation_id=conversation_id,
                        event_callback=event_callback,
                    )
                    logger.info(
                        f"Workflow initiated with ID: {result.get('workflow_id', 'unknown')}"
                    )

                    # Emit acknowledgment that workflow has started but doesn't block on completion
                    await sio.emit(
                        "workflow_started",
                        {
                            "type": "workflow_started",
                            "data": {
                                "workflow_id": result.get("workflow_id", "unknown"),
                                "message": "Your request is being processed by the AI agents",
                                "timestamp": time.time(),
                            },
                        },
                        room=room_name,
                    )

                    # Note: The workflow manager will now handle sending the final response
                    # when execution completes via the event_callback

                except Exception as workflow_error:
                    logger.exception(f"Workflow execution error: {str(workflow_error)}")

                    # Send more detailed error update
                    error_event = {
                        "type": "error",
                        "data": {
                            "message": f"Error processing your request: {str(workflow_error)}",
                            "timestamp": time.time(),
                            "details": {
                                "type": "workflow_error",
                                "query": query[:100] + "..." if len(query) > 100 else query,
                                "error_details": str(workflow_error),
                            },
                        },
                    }
                    logger.debug(f"Emitting error event: {error_event}")
                    await sio.emit("error", error_event, room=room_name)
    except Exception as e:
        logger.exception(f"Socket.IO message error: {str(e)}")
        # Try to send error to client
        try:
            await sio.emit(
                "error",
                {
                    "type": "error",
                    "data": {
                        "message": f"An unexpected error occurred: {str(e)}",
                        "timestamp": time.time(),
                    },
                },
                room=sid,
            )
        except Exception:
            pass  # If this fails too, we've done our best


# Specific agent phase events with enhanced information - IMPROVED IMPLEMENTATION
async def socket_io_agent_event(room: str, event: Dict[str, Any]):
    """Emit agent events to Socket.IO clients in a room.

    Args:
        room: The room to broadcast to
        event: The event data to broadcast
    """
    if not event or not isinstance(event, dict):
        return

    event_type = event.get("type", "agent_update")
    logger.debug(f"Broadcasting agent event type {event_type} to room {room}")

    # Add timestamp to event data if not present
    if "data" in event and isinstance(event["data"], dict) and "timestamp" not in event["data"]:
        event["data"]["timestamp"] = time.time()

    # Enhanced events with progress information
    if "agent" in event:
        agent_type = event["agent"].lower()
        current_phase = ""
        progress = 0.0

        # Add detailed progress tracking based on event type and agent
        if "planner" in agent_type:
            current_phase = "planning"
            if "start" in event_type:
                progress = 0.1
                logger.debug(f"Emitting enhanced planner_start event to room {room}")
                await sio.emit(
                    "planner_start",
                    {
                        "type": "planner_start",
                        "data": {
                            "agent": "planner",
                            "phase": "planning",
                            "message": event.get(
                                "message", "Planning execution strategy based on your query"
                            ),
                            "timestamp": time.time(),
                            "progress": progress,
                        },
                    },
                    room=room,
                )
            elif "progress" in event_type:
                progress = 0.2
                logger.debug(f"Emitting enhanced planner_progress event to room {room}")
                await sio.emit(
                    "planner_progress",
                    {
                        "type": "planner_progress",
                        "data": {
                            "agent": "planner",
                            "phase": "planning",
                            "message": event.get("message", "Planning in progress..."),
                            "timestamp": time.time(),
                            "progress": progress,
                            "details": event.get("details", {}),
                        },
                    },
                    room=room,
                )
            elif "complete" in event_type:
                progress = 0.3
                logger.debug(f"Emitting enhanced planner_complete event to room {room}")
                await sio.emit(
                    "planner_complete",
                    {
                        "type": "planner_complete",
                        "data": {
                            "agent": "planner",
                            "phase": "planning",
                            "message": event.get(
                                "message", "Planning complete, moving to execution phase"
                            ),
                            "timestamp": time.time(),
                            "progress": progress,
                            "details": event.get("details", {}),
                        },
                    },
                    room=room,
                )

        elif "executor" in agent_type:
            current_phase = "executing"
            if "start" in event_type:
                progress = 0.4
                logger.debug(f"Emitting enhanced executor_start event to room {room}")
                await sio.emit(
                    "executor_start",
                    {
                        "type": "executor_start",
                        "data": {
                            "agent": "executor",
                            "phase": "executing",
                            "message": event.get(
                                "message", "Beginning execution of the planned operations"
                            ),
                            "timestamp": time.time(),
                            "progress": progress,
                        },
                    },
                    room=room,
                )
            elif "progress" in event_type:
                # Extract current_step and total_steps if available for dynamic progress
                details = event.get("details", {})
                current_step = details.get("current_step", 0)
                total_steps = details.get("total_steps", 1)

                # Calculate progress between 0.4 and 0.7 based on step count
                if total_steps > 0:
                    step_progress = current_step / total_steps
                    progress = 0.4 + (step_progress * 0.3)  # Map to 0.4-0.7 range
                else:
                    progress = 0.5  # Default mid-execution

                logger.debug(f"Emitting enhanced executor_progress event to room {room}")
                await sio.emit(
                    "executor_progress",
                    {
                        "type": "executor_progress",
                        "data": {
                            "agent": "executor",
                            "phase": "executing",
                            "message": event.get("message", "Executing operations..."),
                            "timestamp": time.time(),
                            "progress": progress,
                            "current_step": current_step,
                            "total_steps": total_steps,
                            "details": details,
                        },
                    },
                    room=room,
                )

                # Also emit a step_update event with more details if this is a step execution
                if "tool" in details or "action" in details:
                    await sio.emit(
                        "step_update",
                        {
                            "type": "step_update",
                            "data": {
                                "step_id": details.get("step_id", current_step),
                                "tool": details.get("tool", "unknown"),
                                "action": details.get("action", "execute"),
                                "description": details.get("description", "Executing operation"),
                                "timestamp": time.time(),
                                "progress": progress,
                                "is_completed": False,
                            },
                        },
                        room=room,
                    )
            elif "complete" in event_type:
                progress = 0.7
                logger.debug(f"Emitting enhanced executor_complete event to room {room}")
                await sio.emit(
                    "executor_complete",
                    {
                        "type": "executor_complete",
                        "data": {
                            "agent": "executor",
                            "phase": "executing",
                            "message": event.get(
                                "message", "Execution complete, starting verification"
                            ),
                            "timestamp": time.time(),
                            "progress": progress,
                            "details": event.get("details", {}),
                        },
                    },
                    room=room,
                )

        elif "verifier" in agent_type:
            current_phase = "verifying"
            if "start" in event_type:
                progress = 0.8
                logger.debug(f"Emitting enhanced verifier_start event to room {room}")
                await sio.emit(
                    "verifier_start",
                    {
                        "type": "verifier_start",
                        "data": {
                            "agent": "verifier",
                            "phase": "verifying",
                            "message": event.get(
                                "message", "Verifying the results of the execution"
                            ),
                            "timestamp": time.time(),
                            "progress": progress,
                        },
                    },
                    room=room,
                )
            elif "progress" in event_type:
                progress = 0.9
                logger.debug(f"Emitting enhanced verifier_progress event to room {room}")
                await sio.emit(
                    "verifier_progress",
                    {
                        "type": "verifier_progress",
                        "data": {
                            "agent": "verifier",
                            "phase": "verifying",
                            "message": event.get("message", "Verification in progress..."),
                            "timestamp": time.time(),
                            "progress": progress,
                            "details": event.get("details", {}),
                        },
                    },
                    room=room,
                )
            elif "complete" in event_type:
                progress = 0.95
                logger.debug(f"Emitting enhanced verifier_complete event to room {room}")
                await sio.emit(
                    "verifier_complete",
                    {
                        "type": "verifier_complete",
                        "data": {
                            "agent": "verifier",
                            "phase": "verifying",
                            "message": event.get(
                                "message", "Verification complete, preparing final response"
                            ),
                            "timestamp": time.time(),
                            "progress": progress,
                            "details": event.get("details", {}),
                        },
                    },
                    room=room,
                )
        elif "response_generator" in agent_type:
            current_phase = "responding"
            if "start" in event_type:
                progress = 0.95
            elif "progress" in event_type:
                progress = 0.97
            elif "complete" in event_type:
                progress = 0.99

        # Add current phase and progress to the event data
        if "data" in event and isinstance(event["data"], dict):
            event["data"]["phase"] = current_phase
            event["data"]["progress"] = progress

    # Handle tool call events specially
    if event_type in ["tool_call_initiated", "tool_call_completed", "tool_call_error"]:
        logger.debug(f"Emitting {event_type} event to room {room}")

        # Ensure we have the proper data structure
        if "data" not in event:
            event["data"] = {}

        # Add timestamp if missing
        if "timestamp" not in event["data"]:
            event["data"]["timestamp"] = time.time()

        # Emit the specific event
        await sio.emit(
            event_type,
            {
                "type": event_type,
                "data": event["data"],
            },
            room=room,
        )

    # Always send the generic agent_update event with enhanced information
    enhanced_event = event.copy()

    # Add timestamp if not present
    if "data" in enhanced_event and isinstance(enhanced_event["data"], dict):
        if "timestamp" not in enhanced_event["data"]:
            enhanced_event["data"]["timestamp"] = time.time()

        # Add phase information
        if "agent_type" in enhanced_event["data"]:
            agent_type = enhanced_event["data"]["agent_type"]
            if "planner" in agent_type:
                enhanced_event["data"]["phase"] = "planning"
            elif "executor" in agent_type:
                enhanced_event["data"]["phase"] = "executing"
            elif "verifier" in agent_type:
                enhanced_event["data"]["phase"] = "verifying"
            else:
                enhanced_event["data"]["phase"] = "processing"

        # Add last_step flag for specific completed events
        if event_type in ["verifier_complete", "response_complete", "workflow_complete"]:
            enhanced_event["data"]["last_step"] = True

            # Add answer from response if available
            if (
                event_type == "response_complete"
                and "details" in event
                and "response" in event["details"]
            ):
                enhanced_event["data"]["answer"] = event["details"]["response"]
            elif "response" in event:
                enhanced_event["data"]["answer"] = event["response"]

    logger.debug(
        f"Emitting enhanced agent_update event to room {room}: {str(enhanced_event)[:200]}..."
    )
    await sio.emit("agent_update", enhanced_event, room=room)


# Terminal output event implementation enhanced for real-time feedback
async def emit_terminal_output(room: str, step_data: Dict[str, Any]):
    """Emit terminal output event to Socket.IO clients in a room.

    Args:
        room: The room to broadcast to
        step_data: The step execution data
    """
    if not step_data or not isinstance(step_data, dict):
        return

    # Extract relevant information
    step_id = step_data.get("step_id", "unknown")
    tool = step_data.get("tool", "command")
    action = step_data.get("action", "execute")
    parameters = step_data.get("parameters", {})
    output = step_data.get("output", "")
    status = step_data.get("status", "unknown")

    # Format command for display
    try:
        command = f"{tool} {action} {json.dumps(parameters)}"
    except:
        command = f"{tool} {action}"

    # Create terminal output event
    terminal_output = {
        "type": "terminal_output",
        "data": {
            "step_id": step_id,
            "tool": tool,
            "action": action,
            "command": command,
            "output": output,
            "timestamp": time.time(),
            "status": status,
        },
    }

    logger.debug(f"Emitting terminal_output event to room {room}: {str(terminal_output)[:200]}...")
    await sio.emit("terminal_output", terminal_output, room=room)

    # Also emit step_complete for UI updates
    step_complete = {
        "type": "step_complete",
        "data": {
            "step_id": step_id,
            "tool": tool,
            "action": action,
            "status": status,
            "timestamp": time.time(),
            "is_completed": True,
        },
    }

    logger.debug(f"Emitting step_complete event to room {room}")
    await sio.emit("step_complete", step_complete, room=room)


@router.post("/conversations")
async def create_conversation(
    request: Request,
    user=Depends(fastapi_users.current_user(optional=True)),
) -> Dict[str, Any]:
    """Create a new conversation with the provided ID or generate a new one."""
    try:
        # Get the conversation ID from the request if provided
        data = await request.json()
        client_conversation_id = data.get("conversation_id")

        if user:
            # Create conversation with user-provided ID or generate one
            conversation_id = client_conversation_id
            if conversation_id:
                try:
                    # Validate UUID format
                    conversation_id = uuid.UUID(conversation_id)
                except ValueError:
                    # If not a valid UUID, generate a new one
                    conversation_id = uuid.uuid4()
            else:
                conversation_id = uuid.uuid4()

            conversation = await Conversation.create(
                id=conversation_id,
                title=data.get("title", f"New Conversation {uuid.uuid4().hex[:8]}"),
                user=user,
            )

            # Create welcome message
            await Message.create(
                conversation=conversation,
                role="system",
                content="Welcome to Skyflo.ai! How can I help you with your Kubernetes infrastructure today?",
                sequence=1,
            )

            logger.info(f"Created new conversation {conversation.id} for user {user.id}")
            return {
                "status": "success",
                "id": str(conversation.id),
                "title": conversation.title,
                "created_at": conversation.created_at.isoformat(),
            }
        else:
            # For unauthenticated users, return the client-provided ID or generate a new one
            conversation_id = client_conversation_id or str(uuid.uuid4())
            logger.info(
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
        # Generate a reliable UUID as fallback
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
        # Get conversations
        conversations = await Conversation.filter(user=user).order_by("-created_at")

        logger.info(f"Retrieved {len(conversations)} conversations for user {user.id}")
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


@router.get("/conversations/{conversation_id}")
async def check_conversation(
    conversation_id: str,
    user=Depends(fastapi_users.current_user(optional=True)),
) -> Dict[str, Any]:
    """Check if a conversation exists."""
    try:
        # Try to get the conversation
        conversation = await get_conversation(conversation_id)

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # If user is authenticated, check permissions
        if user and conversation.user_id != user.id and not user.is_superuser:
            raise HTTPException(
                status_code=403, detail="Not authorized to access this conversation"
            )

        print("Conversation Data:", conversation)

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
        # Get the conversation
        conversation = await get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Check user permissions
        if conversation.user_id != user.id and not user.is_superuser:
            raise HTTPException(
                status_code=403, detail="Not authorized to update this conversation"
            )

        # Get messages from request
        data = await request.json()
        messages = data.get("messages")

        if not messages or not isinstance(messages, list):
            raise HTTPException(status_code=400, detail="Request must include 'messages' as a list")

        # Update messages
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


# Mount the Socket.IO app on a WebSocket route
@router.get("/socket.io/{path_params:path}")
async def socketio_endpoint(path_params: str):
    return sio_app


# Add a specific join event handler that the client can call on reconnect
@sio.event
async def join(sid, data):
    """Handle client joining a conversation manually."""
    try:
        conversation_id = data.get("conversation_id")
        if not conversation_id:
            logger.error(f"No conversation_id provided in join request from {sid}")
            return

        logger.info(f"Client {sid} manually joining conversation {conversation_id}")

        # Add to active connections
        if conversation_id not in active_connections:
            active_connections[conversation_id] = []
        if sid not in active_connections[conversation_id]:
            active_connections[conversation_id].append(sid)

        # Join the room
        room_name = f"conversation:{conversation_id}"
        await sio.enter_room(sid, room_name)

        # Notify client
        await sio.emit(
            "joined_conversation",
            {
                "type": "joined_conversation",
                "data": {
                    "conversation_id": conversation_id,
                    "message": "Successfully joined conversation",
                    "timestamp": time.time(),
                },
            },
            room=sid,
        )
    except Exception as e:
        logger.exception(f"Error in join handler: {str(e)}")
        # Don't disconnect on error, just log it
