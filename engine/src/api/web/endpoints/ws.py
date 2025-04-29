"""Socket.IO endpoints for real-time chat."""

import json
import logging
import uuid
from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime

# Replace WebSocket imports with Socket.IO
from fastapi import APIRouter, Depends, HTTPException, Request
import socketio
from broadcaster import Broadcast
import time

from ...domain.models.conversation import Conversation, Message
from ...services.auth import fastapi_users
from ...workflow import WorkflowManager
from ...config import settings
from ...services.mcp_client import register_global_callback
from ...workflow.agents.executor.main import handle_tool_call_approval, handle_tool_call_rejection

logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, settings.LOG_LEVEL))

router = APIRouter()

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=False,
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=10000000,
    always_connect=True,
)
sio_app = socketio.ASGIApp(sio)

broadcast = Broadcast(settings.REDIS_URL)

active_connections: Dict[str, List[str]] = {}


async def socket_event_callback(event: Dict[str, Any]):
    """Callback for Socket.IO events."""
    # Events can have conversation_id in different locations depending on event type:
    # 1. Directly in the event object for most events
    # 2. Inside 'details' field for agent events
    # 3. Inside 'data' field for tool_call events
    room = None
    if "conversation_id" in event:
        room = f"conversation:{event['conversation_id']}"
    elif (
        "details" in event
        and isinstance(event["details"], dict)
        and "conversation_id" in event["details"]
    ):
        room = f"conversation:{event['details']['conversation_id']}"
    elif "data" in event and isinstance(event["data"], dict) and "conversation_id" in event["data"]:
        room = f"conversation:{event['data']['conversation_id']}"

    if room:
        await socket_io_agent_event(room, event)
    else:
        logger.warning(f"No room found for event: {event.get('type', 'unknown')}")
        logger.warning(f"Event without room: {str(event)[:200]}...")


register_global_callback(socket_event_callback)
logger.debug("Registered socket_event_callback globally")

workflow_manager = WorkflowManager(event_callback=socket_event_callback)


async def get_workflow_manager() -> WorkflowManager:
    return workflow_manager


@router.on_event("startup")
async def startup_event():
    await broadcast.connect()
    logger.debug("Socket.IO broadcaster connected")


@router.on_event("shutdown")
async def shutdown_event():
    await broadcast.disconnect()
    logger.debug("Socket.IO broadcaster disconnected")


async def get_conversation(conversation_id: str) -> Optional[Conversation]:
    try:
        return await Conversation.get(id=conversation_id)
    except Exception as e:
        logger.error(f"Error fetching conversation {conversation_id}: {str(e)}")
        return None


@sio.on("ping")
async def handle_ping(sid, data=None):
    try:
        logger.debug(f"Received ping from client {sid}")
        await sio.emit("pong", {"timestamp": time.time()}, room=sid)
    except Exception as e:
        logger.exception(f"Error in ping handler: {str(e)}")


@sio.on("tool_call_approved")
async def handle_tool_call_approval_message(sid, data=None):
    logger.debug(f"Received tool call approval from client {sid}")
    logger.debug(f"Tool call approval data: {data}")
    handle_tool_call_approval(data["step_id"])


@sio.on("tool_call_rejected")
async def handle_tool_call_rejection_message(sid, data=None):
    logger.debug(f"Received tool call rejection from client {sid}")
    logger.debug(f"Tool call rejection data: {data}")
    handle_tool_call_rejection(data["step_id"])


@sio.event
async def connect(sid, environ, auth=None):
    """Handle Socket.IO connection event."""
    logger.debug(f"Socket.IO client connected: {sid}")

    logger.debug(f"Connection request details for {sid}:")
    logger.debug(f"  - Environment variables: {environ}")
    logger.debug(f"  - Headers: {environ.get('HTTP_HEADERS', {})}")
    logger.debug(f"  - Request path: {environ.get('PATH_INFO', '')}")
    logger.debug(f"  - Remote address: {environ.get('REMOTE_ADDR', 'unknown')}")
    logger.debug(f"  - Protocol: {environ.get('wsgi.url_scheme', 'unknown')}")
    logger.debug(
        f"  - Connection count before connect: {sum(len(clients) for clients in active_connections.values())}"
    )

    try:
        query = environ.get("QUERY_STRING", "")
        logger.debug(f"  - Query string: {query}")

        params = {k: v for k, v in [p.split("=") for p in query.split("&") if "=" in p]}
        auth_token = params.get("token")

        user = None
        if auth_token:
            try:
                from ...services.auth import fastapi_users, auth_backend
                from fastapi_users.jwt import decode_jwt

                logger.debug(f"Verifying auth token for client {sid}")
                decoded_token = decode_jwt(
                    auth_token,
                    settings.JWT_SECRET,
                    audience="fastapi-users:auth",
                )

                user_id = decoded_token.get("sub")
                if user_id:
                    try:
                        from ...services.auth import current_active_user
                        from ...domain.models.user import User

                        user_uuid = uuid.UUID(user_id)
                        user = await User.filter(id=user_uuid).first()

                        if user:
                            logger.debug(f"Authenticated user {user.email} for client {sid}")
                        else:
                            logger.warning(f"User with ID {user_id} not found for client {sid}")
                    except Exception as user_error:
                        logger.warning(
                            f"Failed to retrieve user for client {sid}: {str(user_error)}"
                        )
                else:
                    logger.warning(f"No user ID found in token for client {sid}")
            except Exception as token_error:
                logger.warning(f"Invalid auth token for client {sid}: {str(token_error)}")
        else:
            logger.warning(f"No auth token provided for client {sid}")

        await sio.emit(
            "connected",
            {
                "type": "connected",
                "data": {
                    "authenticated": user is not None,
                    "authorized": True,
                    "message": "WebSocket connection established successfully",
                    "timestamp": time.time(),
                    "connection_id": sid,
                },
            },
            room=sid,
        )

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
async def join_conversation(sid, data):
    """Handle joining a conversation."""
    try:
        conversation_id = data.get("conversation_id")
        if not conversation_id:
            raise ValueError("No conversation_id provided")

        logger.debug(f"Client {sid} joining conversation {conversation_id}")

        if conversation_id not in active_connections:
            active_connections[conversation_id] = []
        active_connections[conversation_id].append(sid)

        await sio.enter_room(sid, f"conversation:{conversation_id}")

        conversation = await get_conversation(conversation_id)
        if not conversation:
            logger.warning(f"Conversation {conversation_id} not found")
            await sio.emit(
                "error",
                {
                    "type": "error",
                    "data": {
                        "message": f"Conversation {conversation_id} not found",
                        "timestamp": time.time(),
                    },
                },
                room=sid,
            )
            return

        messages = await conversation.messages.all().order_by("sequence")
        logger.debug(
            f"Sending {len(messages)} existing messages to client for conversation {conversation_id}"
        )

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
                    "progress": f"{index + 1}/{len(messages)}",
                },
            }
            logger.debug(f"Sending message {index+1}/{len(messages)} to client")
            await sio.emit("message", message_data, room=sid)
            if (index + 1) % 5 == 0 and index + 1 < len(messages):
                await asyncio.sleep(0.01)

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

    except Exception as e:
        logger.exception(f"Error joining conversation: {str(e)}")
        await sio.emit(
            "error",
            {
                "type": "error",
                "data": {
                    "message": f"Error joining conversation: {str(e)}",
                    "timestamp": time.time(),
                },
            },
            room=sid,
        )


@sio.event
async def leave_conversation(sid, data):
    """Handle leaving a conversation."""
    try:
        conversation_id = data.get("conversation_id")
        if not conversation_id:
            raise ValueError("No conversation_id provided")

        logger.debug(f"Client {sid} leaving conversation {conversation_id}")

        if conversation_id in active_connections:
            if sid in active_connections[conversation_id]:
                active_connections[conversation_id].remove(sid)
                if not active_connections[conversation_id]:
                    del active_connections[conversation_id]

        await sio.leave_room(sid, f"conversation:{conversation_id}")

    except Exception as e:
        logger.exception(f"Error leaving conversation: {str(e)}")
        await sio.emit(
            "error",
            {
                "type": "error",
                "data": {
                    "message": f"Error leaving conversation: {str(e)}",
                    "timestamp": time.time(),
                },
            },
            room=sid,
        )


@sio.event
async def disconnect(sid):
    logger.debug(f"Socket.IO client disconnected: {sid}")

    client_rooms = sio.rooms(sid)
    client_conversations = [room for room in client_rooms if room.startswith("conversation:")]

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

    disconnected_from = []
    for conversation_id, clients in list(active_connections.items()):
        if sid in clients:
            clients.remove(sid)
            disconnected_from.append(conversation_id)
            if not clients:
                del active_connections[conversation_id]
            logger.debug(f"Removed client {sid} from conversation {conversation_id}")

    logger.debug(f"Client {sid} disconnected from conversations: {disconnected_from}")
    logger.debug(
        f"Connection count after disconnect: {sum(len(clients) for clients in active_connections.values())}"
    )
    logger.debug(f"Active connections remaining: {active_connections}")


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

    if "data" in event and isinstance(event["data"], dict) and "timestamp" not in event["data"]:
        event["data"]["timestamp"] = time.time()

    if "agent" in event:
        agent_type = event["agent"].lower()
        current_phase = ""
        progress = 0.0

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
                details = event.get("details", {})
                current_step = details.get("current_step", 0)
                total_steps = details.get("total_steps", 1)

                if total_steps > 0:
                    step_progress = current_step / total_steps
                    progress = 0.4 + (step_progress * 0.3)
                else:
                    progress = 0.5

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

        if "data" in event and isinstance(event["data"], dict):
            event["data"]["phase"] = current_phase
            event["data"]["progress"] = progress

    if event_type in ["tool_call_initiated", "tool_call_completed", "tool_call_error"]:
        logger.debug(f"Emitting {event_type} event to room {room}")

        if "data" not in event:
            event["data"] = {}

        if "timestamp" not in event["data"]:
            event["data"]["timestamp"] = time.time()

        await sio.emit(
            event_type,
            {
                "type": event_type,
                "data": event["data"],
            },
            room=room,
        )

    enhanced_event = event.copy()

    if "data" in enhanced_event and isinstance(enhanced_event["data"], dict):
        if "timestamp" not in enhanced_event["data"]:
            enhanced_event["data"]["timestamp"] = time.time()

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

        if event_type in ["verifier_complete", "response_complete", "workflow_complete"]:
            enhanced_event["data"]["last_step"] = True

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

    step_id = step_data.get("step_id", "unknown")
    tool = step_data.get("tool", "command")
    action = step_data.get("action", "execute")
    parameters = step_data.get("parameters", {})
    output = step_data.get("output", "")
    status = step_data.get("status", "unknown")

    try:
        command = f"{tool} {action} {json.dumps(parameters)}"
    except:
        command = f"{tool} {action}"

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


@router.get("/socket.io/{path_params:path}")
async def socketio_endpoint(path_params: str):
    return sio_app
