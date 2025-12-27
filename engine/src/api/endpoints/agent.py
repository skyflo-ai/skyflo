import logging
import json
import asyncio
import uuid
from typing import Dict, Any, Optional, AsyncGenerator
from datetime import datetime

from ..utils.clock import now_ms
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import redis.asyncio as redis

from ..agent.graph import build_graph
from ..models.conversation import Conversation
from ..services.conversation_persistence import ConversationPersistenceService
from ..config import rate_limit_dependency
from ..services.auth import fastapi_users
from ..services.approvals import ApprovalService
from ..config import settings
from .conversation import check_conversation_authorization
from ..services.stop_service import request_stop, clear_stop
from ..services.title_generator import generate_and_store_title
from ..integrations.jenkins import strip_jenkins_metadata_tool_args

logger = logging.getLogger(__name__)

router = APIRouter()

redis_client = None


async def get_redis_client():
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    return redis_client


def sse_format(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def strip_integration_meta_keys(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return payload

    sanitized = dict(payload)
    if "args" in sanitized:
        sanitized["args"] = strip_jenkins_metadata_tool_args(sanitized.get("args", {}))
    if "tools" in sanitized:
        sanitized["tools"] = [
            strip_jenkins_metadata_tool_args(tool) for tool in sanitized.get("tools", [])
        ]
    return sanitized


async def publish_event(channel: str, event: str, payload: Dict[str, Any]):
    r = await get_redis_client()
    try:
        sanitized_payload = strip_integration_meta_keys(payload)
        await r.publish(channel, sse_format(event, sanitized_payload))
    except Exception as e:
        logger.error(f"Error publishing to Redis channel {channel}: {str(e)}")


async def create_sse_event_generator(
    request: Request, channel: str, run_id: str, workflow_kwargs: Dict[str, Any], endpoint_name: str
) -> AsyncGenerator[bytes, None]:
    """Create a reusable SSE event generator for workflow execution."""
    r = await get_redis_client()
    pubsub = r.pubsub()

    try:
        # Subscribe only to the unique run_id channel
        await pubsub.subscribe(channel)

        asyncio.create_task(run_agent_workflow(**workflow_kwargs))

        yield sse_format("ready", {"run_id": run_id}).encode()

        while True:
            if await request.is_disconnected():
                break

            try:
                message = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True), timeout=60.0
                )

                if message and message["type"] == "message":
                    yield (message["data"] + "\n").encode()

                    try:
                        data = json.loads(message["data"].split("\ndata: ")[1].split("\n\n")[0])
                        if data.get("status") in [
                            "completed",
                            "error",
                            "awaiting_approval",
                            "stopped",
                        ]:
                            break
                    except (json.JSONDecodeError, IndexError, KeyError):
                        pass

            except asyncio.TimeoutError:
                yield sse_format("heartbeat", {"timestamp": datetime.now().isoformat()}).encode()

    except Exception as e:
        logger.error(f"Error in {endpoint_name} SSE stream for run {run_id}: {str(e)}")
        yield sse_format("error", {"error": str(e)}).encode()
    finally:
        # Unsubscribe from the channel
        await pubsub.unsubscribe(channel)
        await pubsub.close()


def create_event_callback(
    channel: str,
    conversation_id: Optional[str],
    persistence: Optional[ConversationPersistenceService],
    run_id: Optional[str] = None,
):
    """Create a reusable event callback function for workflow events."""

    async def event_callback(event: Dict[str, Any]):
        event_type = event.get("type", "workflow_event")

        try:
            if "timestamp" not in event and event_type != "token":
                event["timestamp"] = now_ms()
        except Exception:
            pass

        if conversation_id and "conversation_id" not in event:
            event["conversation_id"] = conversation_id

        event_run_id = event.get("run_id") or run_id
        if event_run_id and "run_id" not in event:
            event["run_id"] = event_run_id

        publish_payload = event.copy()
        if event_type == "token.usage" and "cost" in publish_payload:
            del publish_payload["cost"]

        await publish_event(channel, event_type, publish_payload)
        if not persistence or not conversation_id:
            return

        try:
            if event_type == "token.usage" and (event.get("source") or "main") == "main":
                persistence.record_token_usage(
                    conversation_id=conversation_id,
                    run_id=event_run_id,
                    prompt_tokens=int(event.get("prompt_tokens") or 0),
                    completion_tokens=int(event.get("completion_tokens") or 0),
                    total_tokens=int(event.get("total_tokens") or 0),
                    cached_tokens=event.get("cached_tokens"),
                    cost=float(event.get("cost") or 0.0),
                )
                await persistence.apply_usage_snapshot(conversation_id, event_run_id)
            elif event_type == "ttft":
                persistence.record_ttft(
                    conversation_id=conversation_id,
                    run_id=event_run_id,
                    duration_ms=int(event.get("duration") or 0),
                )
                await persistence.apply_usage_snapshot(conversation_id, event_run_id)
            elif event_type == "generation.complete":
                content = str(event.get("content", ""))
                if content:
                    await persistence.append_text_segment(
                        conversation_id=conversation_id,
                        text=content,
                        timestamp=event.get("timestamp"),
                        run_id=event_run_id,
                    )
            elif event_type in ("tool.executing", "tool.awaiting_approval"):
                try:
                    await persistence.update_tool_segment_status(
                        conversation_id=conversation_id,
                        call_id=str(event.get("call_id")),
                        status=(
                            "executing" if event_type == "tool.executing" else "awaiting_approval"
                        ),
                    )
                except Exception:
                    pass

                await persistence.append_tool_segment(
                    conversation_id=conversation_id,
                    tool_execution={
                        "call_id": event.get("call_id"),
                        "tool": event.get("tool"),
                        "title": event.get("title"),
                        "args": event.get("args", {}),
                        "status": (
                            "executing" if event_type == "tool.executing" else "awaiting_approval"
                        ),
                        "timestamp": event.get("timestamp"),
                    },
                    timestamp=int(event.get("timestamp", now_ms())),
                )
            elif event_type == "tools.pending":
                tools_list = event.get("tools") or []
                for tool in tools_list:
                    try:
                        await persistence.append_tool_segment(
                            conversation_id=conversation_id,
                            tool_execution={
                                "call_id": tool.get("call_id"),
                                "tool": tool.get("tool"),
                                "title": tool.get("title"),
                                "args": tool.get("args", {}),
                                "requires_approval": bool(tool.get("requires_approval", False)),
                                "status": "pending",
                                "timestamp": int(tool.get("timestamp", event.get("timestamp"))),
                            },
                            timestamp=int(tool.get("timestamp", event.get("timestamp"))),
                        )
                    except Exception as _:
                        continue
            elif event_type in ("tool.approved", "tool.denied", "tool.error"):
                status_map = {
                    "tool.approved": "approved",
                    "tool.denied": "denied",
                    "tool.error": "error",
                }

                result_blocks = None
                if event_type == "tool.denied":
                    result_blocks = [{"type": "text", "text": "Tool call was denied by the user"}]

                await persistence.update_tool_segment_status(
                    conversation_id=conversation_id,
                    call_id=str(event.get("call_id")),
                    status=status_map.get(event_type, "executing"),
                    error=event.get("error"),
                    result=result_blocks,
                )
            elif event_type == "tool.result":
                await persistence.update_tool_segment_status(
                    conversation_id=conversation_id,
                    call_id=str(event.get("call_id")),
                    status="completed",
                    result=event.get("result"),
                )
            elif event_type == "completed":
                duration_ms = event.get("duration_ms")
                if duration_ms is None:
                    duration = event.get("duration")
                    duration_ms = int(duration * 1000) if isinstance(duration, (int, float)) else None
                persistence.record_ttr(
                    conversation_id=conversation_id,
                    run_id=event_run_id,
                    duration_ms=duration_ms,
                )
                await persistence.finalize_usage_snapshot(conversation_id, event_run_id)
        except Exception as persist_error:
            logger.error(f"Persistence error for conversation {conversation_id}: {persist_error}")

    return event_callback


async def run_agent_workflow(
    run_id: str,
    messages: list[Dict[str, Any]],
    channel: str,
    conversation_id: Optional[str] = None,
    persistence: Optional[ConversationPersistenceService] = None,
    conversation: Optional[Conversation] = None,
    pending_tools: Optional[list[Dict[str, Any]]] = None,
    suppress_pending_event: bool = False,
    approval_decisions: Optional[Dict[str, bool]] = None,
):
    """Unified function to run agent workflow with optional pending tools."""
    try:
        # Clear any lingering stop flag from a previous run so a new message doesn't stop immediately
        try:
            if run_id:
                await clear_stop(run_id)
        except Exception:
            pass

        event_callback = create_event_callback(channel, conversation_id, persistence, run_id=run_id)
        workflow_graph = build_graph(event_callback=event_callback)

        try:
            latest_user_msg = None
            if messages:
                for msg in reversed(messages):
                    if isinstance(msg, dict) and msg.get("role") == "user":
                        latest_user_msg = msg
                        break

            initial_state = {
                "run_id": run_id,
                "messages": [latest_user_msg] if latest_user_msg else [],
                "conversation_id": conversation_id or run_id,
            }

            if suppress_pending_event:
                initial_state["suppress_pending_event"] = True

            if pending_tools is not None:
                initial_state["pending_tools"] = pending_tools

            if approval_decisions is not None:
                initial_state["approval_decisions"] = approval_decisions

            result = await workflow_graph.invoke(initial_state)
            status = "completed"
            if isinstance(result, dict):
                if result.get("awaiting_approval"):
                    status = "awaiting_approval"
                elif result.get("stopped"):
                    status = "stopped"
            await publish_event(
                channel,
                "workflow_complete",
                {"run_id": run_id, "result": result, "status": status},
            )

        finally:
            await workflow_graph.close()

    except Exception as e:
        logger.exception(f"Error in agent workflow for run {run_id}: {str(e)}")
        await publish_event(
            channel, "workflow_error", {"run_id": run_id, "error": str(e), "status": "error"}
        )


def get_sse_response_headers() -> Dict[str, str]:
    """Get standard SSE response headers."""
    return {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Cache-Control",
    }


@router.post("/chat", dependencies=[rate_limit_dependency])
async def chat_stream(request: Request, user=Depends(fastapi_users.current_user(optional=True))):
    try:
        body = await request.json()
        messages = body.get("messages", [])
        conversation_id = body.get("conversation_id")

        if not messages:
            raise HTTPException(status_code=400, detail="messages are required")

        if not any(isinstance(msg, dict) and msg.get("content") for msg in messages):
            raise HTTPException(status_code=400, detail="No valid messages found")

        unique_run_id = str(uuid.uuid4())
        channel = f"run:{unique_run_id}"

        conversation: Optional[Conversation] = None
        persistence: Optional[ConversationPersistenceService] = None
        if conversation_id:
            try:
                conversation = await Conversation.get(id=conversation_id)
            except Exception:
                conversation = None

            if conversation:
                check_conversation_authorization(conversation, user)
                persistence = ConversationPersistenceService()

                try:
                    latest_user = None
                    for msg in reversed(messages):
                        if isinstance(msg, dict) and msg.get("role") == "user":
                            latest_user = msg
                            break
                    if latest_user:
                        await persistence.append_user_message(
                            conversation_id=str(conversation.id),
                            content=str(latest_user.get("content", "")),
                            timestamp=now_ms(),
                        )
                except Exception as e:
                    logger.error(f"Error appending initial user message: {e}")

                try:
                    if not conversation.title:
                        asyncio.create_task(
                            generate_and_store_title(str(conversation.id), persistence)
                        )
                except Exception as e:
                    logger.error(f"Failed to schedule title generation: {e}")

        async def event_generator() -> AsyncGenerator[bytes, None]:
            async for event in create_sse_event_generator(
                request=request,
                channel=channel,
                run_id=unique_run_id,
                workflow_kwargs={
                    "run_id": unique_run_id,
                    "messages": messages,
                    "channel": channel,
                    "conversation_id": conversation_id,
                    "persistence": persistence,
                    "conversation": conversation,
                },
                endpoint_name="chat",
            ):
                yield event

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers=get_sse_response_headers(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error setting up SSE stream: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error setting up stream: {str(e)}")


class ApprovalDecision(BaseModel):
    approve: bool = Field(..., description="Whether to approve the tool call")
    reason: Optional[str] = Field(None, description="Optional reason for the decision")
    conversation_id: Optional[str] = Field(
        None, description="Conversation to resume (same as run_id)"
    )


approval_service = ApprovalService()


async def get_approval_service() -> ApprovalService:
    return approval_service


@router.post("/approvals/{call_id}", dependencies=[rate_limit_dependency])
async def decide_approval(
    call_id: str,
    request: Request,
    approval_service: ApprovalService = Depends(get_approval_service),
    user=Depends(fastapi_users.current_user(optional=True)),
):
    try:
        body = await request.json()
        decision = ApprovalDecision(**body)
        user_id = str(user.id) if user else None

        conversation_id = decision.conversation_id
        if not conversation_id:
            raise HTTPException(status_code=400, detail="conversation_id is required")

        unique_run_id = str(uuid.uuid4())
        channel = f"run:{unique_run_id}"

        conversation: Optional[Conversation] = None
        persistence: Optional[ConversationPersistenceService] = None
        try:
            conversation = await Conversation.get(id=conversation_id)
            if conversation:
                check_conversation_authorization(conversation, user)
                persistence = ConversationPersistenceService()
        except Exception as e:
            pass

        if not decision.approve:
            if persistence and conversation:
                try:
                    await persistence.update_tool_segment_status(
                        conversation_id=conversation_id,
                        call_id=call_id,
                        status="denied",
                        result=[{"type": "text", "text": "Tool call was denied by the user"}],
                    )
                except Exception as e:
                    logger.error(f"Failed to update denied tool in persistence: {e}")

        async def event_generator() -> AsyncGenerator[bytes, None]:
            async for event in create_sse_event_generator(
                request=request,
                channel=channel,
                run_id=unique_run_id,
                workflow_kwargs={
                    "run_id": unique_run_id,
                    "messages": [],
                    "channel": channel,
                    "conversation_id": conversation_id,
                    "persistence": persistence,
                    "conversation": conversation,
                    "pending_tools": None,
                    "suppress_pending_event": True,
                    "approval_decisions": {call_id: bool(decision.approve)},
                },
                endpoint_name="approval",
            ):
                yield event

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers=get_sse_response_headers(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error processing approval decision: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing approval: {str(e)}")


class StopRequest(BaseModel):
    conversation_id: str = Field(..., description="Conversation ID for authorization")
    run_id: str = Field(..., description="Specific run to stop")


@router.post("/stop", dependencies=[rate_limit_dependency])
async def stop_run(request: Request, user=Depends(fastapi_users.current_user(optional=True))):
    try:
        body = await request.json()
        req = StopRequest(**body)

        conversation: Optional[Conversation] = None
        try:
            conversation = await Conversation.get(id=req.conversation_id)
        except Exception:
            pass

        if conversation:
            check_conversation_authorization(conversation, user)

        await request_stop(req.run_id)

        run_channel = f"run:{req.run_id}"
        await publish_event(
            run_channel,
            "workflow_complete",
            {"run_id": req.run_id, "result": {"done": True}, "status": "stopped"},
        )

        return {"status": "stopped", "conversation_id": req.conversation_id, "run_id": req.run_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error requesting stop: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error requesting stop: {str(e)}")
