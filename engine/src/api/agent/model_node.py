import asyncio
import json
import uuid
import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Callable, Awaitable, Literal

from litellm import acompletion
from litellm.exceptions import RateLimitError
from pydantic import BaseModel, Field

from ..config import settings
from ..utils.helpers import get_api_key_for_provider, get_state_value
from ..utils.sanitization import (
    sanitize_messages_for_openai,
    sanitize_messages_for_gemini,
    mcp_tools_to_openai_format,
    prepare_messages_with_system_prompt,
)
from .prompts import NEXT_SPEAKER_CHECK_PROMPT
from .stop import StopRequested
from ..services.stop_service import should_stop

logger = logging.getLogger(__name__)

EventCallback = Callable[[Dict[str, Any]], Awaitable[None]]


class NextSpeakerDecision(BaseModel):
    reasoning: str = Field(..., description="Brief explanation of the decision")
    next_speaker: Literal["user", "model"] = Field(..., description="Who should speak next")


async def decide_next_speaker(
    messages: List[Dict[str, Any]], model: str, api_key: Optional[str] = None
) -> str:
    curated = messages[-6:] if len(messages) > 6 else messages
    curated = sanitize_messages_for_openai(curated)
    judge_messages = curated + [{"role": "user", "content": NEXT_SPEAKER_CHECK_PROMPT}]

    completion_kwargs = {
        "model": model,
        "messages": judge_messages,
        "response_format": NextSpeakerDecision,
        "temperature": 0.0,
        "max_tokens": 200,
    }

    if api_key:
        completion_kwargs["api_key"] = api_key

    try:
        resp = await acompletion(**completion_kwargs)
        parsed = NextSpeakerDecision.model_validate_json(resp.choices[0].message.content)
        return parsed.next_speaker
    except Exception as e:
        return "user"


async def run_model_turn(
    messages: List[Dict[str, Any]],
    event_callback: Optional[EventCallback] = None,
    conversation_id: Optional[str] = None,
    run_id: Optional[str] = None,
    max_retries: int = 3,
    tools_provider: Optional[Callable[[], Awaitable[List[Dict[str, Any]]]]] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    retry_count = 0
    last_exception = None

    while retry_count <= max_retries:
        try:
            tools: List[Dict[str, Any]] = []
            try:
                if tools_provider:
                    tools = await tools_provider()
                if tools and not _validate_tools_schema(tools):
                    tools = []
            except Exception as e:
                tools = []

            model = settings.LLM_MODEL
            temperature = settings.LLM_TEMPERATURE or 0.2
            temperature = max(0.0, min(2.0, temperature))

            provider = model.split("/")[0] if "/" in model else "openai"
            api_key = get_api_key_for_provider(provider)

            prepared_messages = prepare_messages_with_system_prompt(messages)
            prepared_messages = sanitize_messages_for_openai(prepared_messages)

            if not _validate_messages_format(prepared_messages):
                raise ValueError("Invalid message format detected")

            if tools and provider == "gemini":
                tools = sanitize_messages_for_gemini(tools)

            completion_kwargs = {
                "model": model,
                "messages": prepared_messages,
                "stream": True,
                "tools": tools if tools else None,
                "tool_choice": "auto" if tools else None,
                "temperature": temperature,
                "max_tokens": 4000,
                "timeout": 120,
            }

            if api_key:
                completion_kwargs["api_key"] = api_key

            if hasattr(settings, "LLM_HOST") and settings.LLM_HOST:
                completion_kwargs["api_base"] = settings.LLM_HOST

            if event_callback:
                await event_callback(
                    {
                        "type": "generation.start",
                        "model": model,
                        "conversation_id": conversation_id,
                        "tools_available": len(tools),
                    }
                )

            response = await acompletion(**completion_kwargs)

            assistant_messages = []
            tool_calls = []
            content_buffer = ""
            tool_calls_buffer = {}
            tokens_generated = 0

            try:
                async for chunk in response:
                    # Check for stop using run_id for the new architecture
                    if run_id and tokens_generated % 25 == 0:
                        if await should_stop(run_id):
                            raise StopRequested()
                    if not chunk.choices:
                        continue

                    choice = chunk.choices[0]
                    delta = choice.delta

                    if hasattr(delta, "content") and delta.content:
                        content_buffer += delta.content
                        tokens_generated += 1

                        if event_callback:
                            await event_callback(
                                {
                                    "type": "token",
                                    "text": delta.content,
                                    "conversation_id": conversation_id,
                                    "tokens_generated": tokens_generated,
                                }
                            )

                    if hasattr(delta, "tool_calls") and delta.tool_calls:
                        for tool_call in delta.tool_calls:
                            if not hasattr(tool_call, "index"):
                                continue

                            index = tool_call.index

                            if index not in tool_calls_buffer:
                                tool_calls_buffer[index] = {"id": "", "name": "", "arguments": ""}

                            if hasattr(tool_call, "id") and tool_call.id:
                                if not tool_calls_buffer[index]["id"]:
                                    tool_calls_buffer[index]["id"] = tool_call.id

                            if (
                                hasattr(tool_call, "function")
                                and hasattr(tool_call.function, "name")
                                and tool_call.function.name
                            ):
                                tool_calls_buffer[index]["name"] += tool_call.function.name

                            if (
                                hasattr(tool_call, "function")
                                and hasattr(tool_call.function, "arguments")
                                and tool_call.function.arguments
                            ):
                                tool_calls_buffer[index][
                                    "arguments"
                                ] += tool_call.function.arguments

            except Exception as stream_error:
                logger.error(f"Error during streaming: {stream_error}")
                if not (content_buffer or tool_calls_buffer):
                    raise stream_error

            assistant_message: Dict[str, Any] = {
                "role": "assistant",
                "content": content_buffer or "",
            }

            if tool_calls_buffer:
                formatted_tool_calls: List[Dict[str, Any]] = []
                for index, tool_call in tool_calls_buffer.items():
                    call_id = (tool_call.get("id") or f"call_{uuid.uuid4().hex}").strip()
                    call_name = (tool_call.get("name") or "").strip()
                    call_args = tool_call.get("arguments") or "{}"
                    formatted_tool_calls.append(
                        {
                            "id": call_id,
                            "type": "function",
                            "function": {"name": call_name, "arguments": call_args},
                        }
                    )
                    tool_calls_buffer[index]["id"] = call_id
                assistant_message["tool_calls"] = formatted_tool_calls

            if assistant_message.get("content") or assistant_message.get("tool_calls"):
                assistant_messages.append(assistant_message)

            for index, tool_call in tool_calls_buffer.items():
                try:
                    tool_name = tool_call["name"].strip()
                    if not tool_name:
                        continue

                    available_tool_names = [tool["function"]["name"] for tool in tools]
                    if tool_name not in available_tool_names:
                        continue

                    args = {}
                    if tool_call["arguments"]:
                        try:
                            args = json.loads(tool_call["arguments"])
                            if not isinstance(args, dict):
                                args = {}
                        except json.JSONDecodeError as e:
                            try:
                                fixed_args = _fix_json_arguments(tool_call["arguments"])
                                args = json.loads(fixed_args)
                            except:
                                args = {}

                    call_id = (tool_call.get("id") or f"call_{uuid.uuid4().hex}").strip()
                    tool_calls.append({"id": call_id, "name": tool_name, "args": args})

                except Exception as e:
                    logger.error(f"Error processing tool call {index}: {str(e)}")
                    continue

            if event_callback:
                await event_callback(
                    {
                        "type": "generation.complete",
                        "conversation_id": conversation_id,
                        "tokens_generated": tokens_generated,
                        "tool_calls": len(tool_calls),
                        "content": content_buffer,
                    }
                )

            return assistant_messages, tool_calls

        except RateLimitError as e:
            retry_count += 1
            last_exception = e

            if retry_count <= max_retries:
                wait_time = min(60, 2**retry_count)
                logger.warning(
                    f"Rate limit hit, retrying in {wait_time}s (attempt {retry_count}/{max_retries})"
                )

                if event_callback:
                    await event_callback(
                        {
                            "type": "rate_limit",
                            "retry_in": wait_time,
                            "attempt": retry_count,
                            "max_retries": max_retries,
                        }
                    )

                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Rate limit error after {max_retries} retries: {str(e)}")
                raise

        except Exception as e:
            retry_count += 1
            last_exception = e

            if _is_transient_error(e) and retry_count <= max_retries:
                wait_time = min(30, 2**retry_count)
                logger.warning(
                    f"Transient error, retrying in {wait_time}s (attempt {retry_count}/{max_retries}): {e}"
                )

                if event_callback:
                    await event_callback(
                        {
                            "type": "transient_error",
                            "error": str(e),
                            "retry_in": wait_time,
                            "attempt": retry_count,
                        }
                    )

                await asyncio.sleep(wait_time)
            else:
                logger.exception(f"Error in model turn: {str(e)}")
                raise

    logger.error(f"Model turn failed after {max_retries} retries")
    raise last_exception or Exception("Model turn failed after maximum retries")


def _validate_tools_schema(tools: List[Dict[str, Any]]) -> bool:
    if not isinstance(tools, list):
        return False

    for tool in tools:
        if not isinstance(tool, dict):
            return False
        if "type" not in tool or tool["type"] != "function":
            return False
        if "function" not in tool or not isinstance(tool["function"], dict):
            return False
        function = tool["function"]
        if "name" not in function or not isinstance(function["name"], str):
            return False

    return True


def _validate_messages_format(messages: List[Dict[str, Any]]) -> bool:
    if not isinstance(messages, list) or not messages:
        return False

    for msg in messages:
        if not isinstance(msg, dict):
            return False
        if "role" not in msg or msg["role"] not in ["system", "user", "assistant", "tool"]:
            return False
        if "content" not in msg:
            return False

    return True


def _fix_json_arguments(args_str: str) -> str:
    fixed = args_str.strip()
    fixed = re.sub(r",(\s*[}\]])", r"\1", fixed)
    fixed = re.sub(r"(\w+):", r'"\1":', fixed)
    fixed = fixed.replace("'", '"')
    return fixed


def _is_transient_error(error: Exception) -> bool:
    transient_indicators = [
        "timeout",
        "connection",
        "network",
        "503",
        "502",
        "504",
        "temporarily unavailable",
        "try again",
        "rate limit",
    ]

    error_str = str(error).lower()
    return any(indicator in error_str for indicator in transient_indicators)


class ModelNode:
    def __init__(
        self,
        event_callback: Optional[EventCallback] = None,
        tools_provider: Optional[Callable[[], Awaitable[List[Dict[str, Any]]]]] = None,
    ):
        self.event_callback = event_callback
        self.tools_provider = tools_provider

    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        try:
            run_id = get_state_value(state, "run_id")
            if await should_stop(run_id):
                raise StopRequested()

            auto_turns = get_state_value(state, "auto_continue_turns", 0)

            if auto_turns > 0:
                auto_decrement_delta = {"auto_continue_turns": max(0, auto_turns - 1)}

            messages = get_state_value(state, "messages", [])
            conversation_id = get_state_value(state, "conversation_id")

            if not messages:
                return {"messages": [], "pending_tools": [], "error": "No messages provided"}

            assistant_msgs, tool_calls = await run_model_turn(
                messages=messages,
                event_callback=self.event_callback,
                conversation_id=conversation_id,
                run_id=run_id,
                max_retries=3,
                tools_provider=self.tools_provider,
            )

            updated_state = {"messages": assistant_msgs}

            if tool_calls:
                updated_state["pending_tools"] = tool_calls
                tool_names = [tool["name"] for tool in tool_calls]
            else:
                model = settings.LLM_MODEL
                provider = model.split("/")[0] if "/" in model else "openai"
                api_key = get_api_key_for_provider(provider)

                decision_context = get_state_value(state, "messages", []) + assistant_msgs
                decision = await decide_next_speaker(decision_context, model, api_key)

                if decision == "model":
                    if get_state_value(state, "awaiting_approval", False):
                        updated_state.setdefault("pending_tools", [])
                        if auto_turns > 0:
                            updated_state.update({"auto_continue_turns": max(0, auto_turns - 1)})
                        return updated_state
                    updated_state["messages"] = updated_state["messages"] + [
                        {"role": "user", "content": "Please continue."}
                    ]
                    max_auto_turns = getattr(settings, "MAX_AUTO_CONTINUE_TURNS", 2)
                    current_auto_turns = get_state_value(state, "auto_continue_turns", 0)
                    updated_state["auto_continue_turns"] = min(
                        current_auto_turns + 1, max_auto_turns
                    )

                updated_state.setdefault("pending_tools", [])

            if auto_turns > 0 and "auto_continue_turns" not in updated_state:
                updated_state.update(auto_decrement_delta)

            return updated_state

        except Exception as e:
            logger.exception(f"Error in model node: {str(e)}")
            return {
                "messages": [
                    {
                        "role": "assistant",
                        "content": f"Error in model turn: {str(e)}",
                    }
                ],
                "pending_tools": [],
                "error": str(e),
            }
