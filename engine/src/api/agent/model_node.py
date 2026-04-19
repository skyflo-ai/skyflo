import asyncio
import json
import logging
import re
import time
import uuid
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

import litellm
from litellm import acompletion, cost_per_token
from litellm.exceptions import RateLimitError

from ..config import settings
from ..services.stop_service import should_stop
from ..utils.clock import now_ms
from ..utils.helpers import get_api_key_for_provider, get_state_value
from ..utils.sanitization import (
    prepare_messages_with_system_prompt,
    sanitize_messages_for_gemini,
    sanitize_messages_for_openai,
    window_messages,
)
from .stop import StopRequested

# Required to transform params for reasoning and thinking features.
litellm.modify_params = True

logger = logging.getLogger(__name__)

PROVIDERS_NOT_SUPPORTING_REASONING_CONTENT = frozenset[str]({"openai", "qwen"})

_MAX_TOOL_CALL_ID_LENGTH = 128

EventCallback = Callable[[Dict[str, Any]], Awaitable[None]]


def _make_display_call_id(raw_id: str) -> str:
    """Derive a short, URL-safe call ID for the approval workflow.

    LiteLLM's Responses API translation for some providers (notably Gemini)
    embeds the full reasoning/thinking payload in the ``tool_call.id`` using a
    ``__thought__`` sentinel.  These IDs can be thousands of characters long and
    break URL-based approval endpoints.
    """
    short = raw_id
    if "__thought__" in short:
        short = short.split("__thought__")[0].rstrip("_")
    if not short or len(short) > _MAX_TOOL_CALL_ID_LENGTH:
        return f"call_{uuid.uuid4().hex}"
    return short


def _get_reasoning_config(model: str) -> Dict[str, Any]:
    """Determine reasoning configuration for the model.

    Priority:
    1. Explicit env vars (LLM_THINKING_BUDGET_TOKENS, LLM_REASONING_EFFORT)
    2. Auto-detection via litellm.supports_reasoning()
    3. Disabled (safe default for unknown models)
    """
    if (
        settings.LLM_THINKING_BUDGET_TOKENS is not None
        and settings.LLM_REASONING_EFFORT is not None
    ):
        logger.warning(
            "Both LLM_THINKING_BUDGET_TOKENS and LLM_REASONING_EFFORT are set. "
            "Using LLM_THINKING_BUDGET_TOKENS"
        )

    if settings.LLM_THINKING_BUDGET_TOKENS is not None:
        return {
            "enabled": True,
            "thinking_budget": settings.LLM_THINKING_BUDGET_TOKENS,
        }

    if settings.LLM_REASONING_EFFORT is not None:
        return {
            "enabled": True,
            "reasoning_effort": settings.LLM_REASONING_EFFORT,
        }

    try:
        if litellm.supports_reasoning(model=model):
            return {
                "enabled": True,
                "reasoning_effort": "high",
            }
    except Exception as e:
        logger.debug(f"Could not auto-detect reasoning support for {model}: {e}")

    return {"enabled": False}


ToolsProvider = Callable[[Optional[Dict[str, bool]]], Awaitable[List[Dict[str, Any]]]]


_ANTHROPIC_CACHE_PROVIDERS = frozenset({"anthropic", "bedrock", "vertex_ai"})


def _supports_prompt_caching(model: str, provider: str) -> bool:
    """Detect whether the target model supports Anthropic-style prompt caching.

    The ``cache_control_injection_points`` request parameter is the litellm
    transform for Anthropic's prompt caching protocol. It applies to Claude
    on the native Anthropic API as well as Claude on Bedrock and Vertex AI.
    Other providers (OpenAI, Gemini, etc.) cache automatically and must not
    receive this parameter.
    """
    if provider == "anthropic":
        return True
    if provider in _ANTHROPIC_CACHE_PROVIDERS and "claude" in model.lower():
        return True
    return False


async def run_model_turn(
    messages: List[Dict[str, Any]],
    event_callback: Optional[EventCallback] = None,
    conversation_id: Optional[str] = None,
    run_id: Optional[str] = None,
    max_retries: int = 3,
    tools_provider: Optional[ToolsProvider] = None,
    loaded_toolsets: Optional[Dict[str, Any]] = None,
    start_time: Optional[float] = None,
    ttft_emitted: bool = False,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], bool]:
    retry_count = 0
    last_exception = None
    new_ttft_emitted = False

    async def emit_ttft_if_needed():
        nonlocal new_ttft_emitted
        if not ttft_emitted and not new_ttft_emitted and start_time:
            ttft_duration = now_ms() - int(start_time * 1000)
            await event_callback(
                {
                    "type": "ttft",
                    "duration": ttft_duration,
                    "timestamp": now_ms(),
                    "run_id": run_id,
                }
            )
            new_ttft_emitted = True

    while retry_count <= max_retries:
        try:
            tools: List[Dict[str, Any]] = []
            try:
                if tools_provider:
                    tools = await tools_provider(loaded_toolsets)
                if tools and not _validate_tools_schema(tools):
                    tools = []
            except Exception as e:
                logger.warning(f"Failed to load tools, proceeding without: {e}")
                tools = []

            model = settings.LLM_MODEL

            provider = model.split("/")[0] if "/" in model else "openai"
            api_key = get_api_key_for_provider(provider)

            reasoning_cfg = _get_reasoning_config(model)
            reasoning_enabled = reasoning_cfg["enabled"]

            windowed = window_messages(messages)
            prepared_messages = prepare_messages_with_system_prompt(windowed)
            prepared_messages = sanitize_messages_for_openai(prepared_messages)

            model_parts = set(model.split("/"))
            if not model_parts.isdisjoint(PROVIDERS_NOT_SUPPORTING_REASONING_CONTENT):
                prepared_messages = _strip_reasoning_content(prepared_messages)
            elif reasoning_enabled or _has_reasoning_content(prepared_messages):
                prepared_messages = _ensure_reasoning_content(prepared_messages)

            if not _validate_messages_format(prepared_messages):
                raise ValueError("Invalid message format detected")

            if tools and provider == "gemini":
                tools = sanitize_messages_for_gemini(tools)

            completion_kwargs = {
                "model": model,
                "messages": prepared_messages,
                "stream": True,
                "stream_options": {"include_usage": True},
                "tools": tools if tools else None,
                "tool_choice": "auto" if tools else None,
                "timeout": 120,
                "drop_params": True,
            }

            if "thinking_budget" in reasoning_cfg:
                budget = reasoning_cfg["thinking_budget"]
                completion_kwargs["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": budget,
                }
                if settings.LLM_MAX_TOKENS:
                    completion_kwargs["max_tokens"] = settings.LLM_MAX_TOKENS
                else:
                    completion_kwargs["max_tokens"] = max(budget * 2, 16384)
            elif "reasoning_effort" in reasoning_cfg:
                completion_kwargs["reasoning_effort"] = reasoning_cfg["reasoning_effort"]

            if api_key:
                completion_kwargs["api_key"] = api_key

            if hasattr(settings, "LLM_HOST") and settings.LLM_HOST:
                completion_kwargs["api_base"] = settings.LLM_HOST

            if _supports_prompt_caching(model, provider):
                completion_kwargs["cache_control_injection_points"] = [
                    {"location": "message", "role": "system"},
                    {"location": "tool_config"},
                ]

            if event_callback:
                await event_callback(
                    {
                        "type": "generation.start",
                        "model": model,
                        "conversation_id": conversation_id,
                        "tools_available": len(tools),
                        "run_id": run_id,
                    }
                )

            response = await acompletion(**completion_kwargs)

            assistant_messages = []
            tool_calls = []
            content_buffer = ""
            thinking_buffer = ""
            thinking_start_time: Optional[float] = None
            tool_calls_buffer = {}
            tool_call_id_to_index = {}
            next_internal_index = 0
            last_seen_id_for_reported_index = {}
            tokens_generated = 0
            thinking_tokens_generated = 0
            stream_usage = None

            try:
                async for chunk in response:
                    if run_id and (tokens_generated + thinking_tokens_generated) % 25 == 0:
                        if await should_stop(run_id):
                            raise StopRequested()

                    if hasattr(chunk, "usage") and chunk.usage:
                        stream_usage = chunk.usage

                    if not chunk.choices:
                        continue

                    choice = chunk.choices[0]
                    delta = choice.delta

                    if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                        if not thinking_buffer:
                            thinking_start_time = time.monotonic()
                        thinking_buffer += delta.reasoning_content
                        thinking_tokens_generated += 1

                        if event_callback:
                            await emit_ttft_if_needed()
                            await event_callback(
                                {
                                    "type": "thinking",
                                    "text": delta.reasoning_content,
                                    "conversation_id": conversation_id,
                                    "run_id": run_id,
                                }
                            )

                    if hasattr(delta, "content") and delta.content:
                        content_buffer += delta.content
                        tokens_generated += 1

                        if event_callback:
                            await emit_ttft_if_needed()

                            await event_callback(
                                {
                                    "type": "token",
                                    "text": delta.content,
                                    "conversation_id": conversation_id,
                                    "tokens_generated": tokens_generated,
                                    "run_id": run_id,
                                }
                            )

                    if hasattr(delta, "tool_calls") and delta.tool_calls:
                        if event_callback:
                            await emit_ttft_if_needed()

                        # LiteLLM's Responses API -> Chat Completions translation (only for openai)
                        # reports all tool calls with index=0 and re-sends the
                        # tool name on both "added" and "done" events. We use
                        # the unique call_id to assign each tool call its own
                        # buffer slot, and set the name only once to prevent
                        # duplication (e.g. "k8s_getk8s_get").
                        for tool_call in delta.tool_calls:
                            if not hasattr(tool_call, "index"):
                                continue

                            reported_index = tool_call.index
                            tc_id = (
                                tool_call.id if hasattr(tool_call, "id") and tool_call.id else None
                            )

                            if tc_id:
                                if tc_id not in tool_call_id_to_index:
                                    tool_call_id_to_index[tc_id] = next_internal_index
                                    next_internal_index += 1
                                index = tool_call_id_to_index[tc_id]
                                last_seen_id_for_reported_index[reported_index] = tc_id
                            else:
                                last_id = last_seen_id_for_reported_index.get(reported_index)
                                if last_id and last_id in tool_call_id_to_index:
                                    index = tool_call_id_to_index[last_id]
                                else:
                                    index = reported_index

                            if index not in tool_calls_buffer:
                                tool_calls_buffer[index] = {
                                    "id": "",
                                    "name": "",
                                    "arguments": "",
                                }

                            if tc_id and not tool_calls_buffer[index]["id"]:
                                tool_calls_buffer[index]["id"] = tc_id

                            if (
                                hasattr(tool_call, "function")
                                and hasattr(tool_call.function, "name")
                                and tool_call.function.name
                                and not tool_calls_buffer[index]["name"]
                            ):
                                tool_calls_buffer[index]["name"] = tool_call.function.name

                            if (
                                hasattr(tool_call, "function")
                                and hasattr(tool_call.function, "arguments")
                                and tool_call.function.arguments
                            ):
                                tool_calls_buffer[index]["arguments"] += (
                                    tool_call.function.arguments
                                )

            except Exception as stream_error:
                logger.error(f"Error during streaming: {stream_error}")
                if not (content_buffer or thinking_buffer or tool_calls_buffer):
                    raise stream_error

            if event_callback and stream_usage:
                cached_tokens = None
                if (
                    hasattr(stream_usage, "prompt_tokens_details")
                    and stream_usage.prompt_tokens_details
                ):
                    cached_tokens = getattr(
                        stream_usage.prompt_tokens_details, "cached_tokens", None
                    )

                prompt_tokens = getattr(stream_usage, "prompt_tokens", 0) or 0
                completion_tokens = getattr(stream_usage, "completion_tokens", 0) or 0

                cost = 0.0
                try:
                    p_cost, c_cost = cost_per_token(
                        model=model,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        cache_read_input_tokens=cached_tokens or 0,
                    )
                    cost = p_cost + c_cost
                except Exception as e:
                    logger.debug(f"Error calculating cost: {e}")

                await event_callback(
                    {
                        "type": "token.usage",
                        "source": "main",
                        "model": model,
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": getattr(stream_usage, "total_tokens", 0) or 0,
                        "cached_tokens": cached_tokens,
                        "cost": cost,
                        "conversation_id": conversation_id,
                        "timestamp": now_ms(),
                        "run_id": run_id,
                    }
                )

            if thinking_buffer and event_callback:
                thinking_duration_ms = (
                    int((time.monotonic() - thinking_start_time) * 1000)
                    if thinking_start_time
                    else 0
                )
                await event_callback(
                    {
                        "type": "thinking.complete",
                        "content": thinking_buffer,
                        "duration_ms": thinking_duration_ms,
                        "conversation_id": conversation_id,
                        "run_id": run_id,
                    }
                )

            assistant_message: Dict[str, Any] = {
                "role": "assistant",
                "content": content_buffer or "",
            }

            if thinking_buffer:
                assistant_message["reasoning_content"] = thinking_buffer

            if tool_calls_buffer:
                formatted_tool_calls: List[Dict[str, Any]] = []
                for index, tool_call in tool_calls_buffer.items():
                    original_id = (tool_call.get("id") or f"call_{uuid.uuid4().hex}").strip()
                    call_name = (tool_call.get("name") or "").strip()
                    call_args = tool_call.get("arguments") or "{}"
                    formatted_tool_calls.append(
                        {
                            "id": original_id,
                            "type": "function",
                            "function": {"name": call_name, "arguments": call_args},
                        }
                    )
                    tool_calls_buffer[index]["id"] = original_id
                    tool_calls_buffer[index]["call_id"] = _make_display_call_id(original_id)
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
                    raw_args = tool_call.get("arguments")
                    if raw_args:
                        if isinstance(raw_args, dict):
                            args = raw_args
                        else:
                            try:
                                args = json.loads(raw_args)
                                if not isinstance(args, dict):
                                    args = {}
                            except (json.JSONDecodeError, TypeError):
                                try:
                                    fixed_args = _fix_json_arguments(str(raw_args))
                                    args = json.loads(fixed_args)
                                    if not isinstance(args, dict):
                                        args = {}
                                except Exception as e:
                                    logger.debug(f"Failed to parse tool args for {tool_name}: {e}")
                                    args = {}

                    original_id = (tool_call.get("id") or f"call_{uuid.uuid4().hex}").strip()
                    display_id = tool_call.get("call_id") or _make_display_call_id(original_id)
                    tool_calls.append(
                        {
                            "id": original_id,
                            "call_id": display_id,
                            "name": tool_name,
                            "args": args,
                        }
                    )

                except Exception as e:
                    logger.error(f"Error processing tool call {index}: {str(e)}")
                    continue

            if event_callback:
                gen_complete_payload = {
                    "type": "generation.complete",
                    "conversation_id": conversation_id,
                    "tokens_generated": tokens_generated,
                    "tool_calls": len(tool_calls),
                    "content": content_buffer,
                    "run_id": run_id,
                }
                if thinking_buffer:
                    gen_complete_payload["thinking_content"] = thinking_buffer
                await event_callback(gen_complete_payload)

            return assistant_messages, tool_calls, (ttft_emitted or new_ttft_emitted)

        except RateLimitError as e:
            retry_count += 1
            last_exception = e

            if retry_count <= max_retries:
                wait_time = min(60, 2**retry_count)
                logger.warning(
                    f"Rate limit hit, retrying in {wait_time}s "
                    f"(attempt {retry_count}/{max_retries})"
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
                    f"Transient error, retrying in {wait_time}s "
                    f"(attempt {retry_count}/{max_retries}): {e}"
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


def _has_reasoning_content(messages: List[Dict[str, Any]]) -> bool:
    """Check if any assistant message already carries reasoning_content.

    Used for runtime auto-detection: if the model previously produced
    reasoning_content, it requires the field on all assistant messages.
    """
    return any(msg.get("role") == "assistant" and "reasoning_content" in msg for msg in messages)


def _ensure_reasoning_content(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Ensure all assistant messages have reasoning_content when thinking is enabled.

    Some providers (e.g. Moonshot/Kimi) reject requests where thinking is
    enabled but an assistant message -- particularly one carrying tool_calls --
    is missing the reasoning_content field.
    """
    result = []
    for msg in messages:
        if msg.get("role") == "assistant" and "reasoning_content" not in msg:
            msg = {**msg, "reasoning_content": ""}
        result.append(msg)
    return result


def _strip_reasoning_content(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove reasoning_content from all messages for providers that reject it."""
    result = []
    for msg in messages:
        if msg.get("role") == "assistant" and "reasoning_content" in msg:
            msg = {k: v for k, v in msg.items() if k != "reasoning_content"}
        result.append(msg)
    return result


def _validate_messages_format(messages: List[Dict[str, Any]]) -> bool:
    if not isinstance(messages, list) or not messages:
        return False

    for msg in messages:
        if not isinstance(msg, dict):
            return False
        if "role" not in msg or msg["role"] not in [
            "system",
            "user",
            "assistant",
            "tool",
        ]:
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
        tools_provider: Optional[ToolsProvider] = None,
    ):
        self.event_callback = event_callback
        self.tools_provider = tools_provider

    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        try:
            run_id = get_state_value(state, "run_id")
            if await should_stop(run_id):
                raise StopRequested()

            messages = get_state_value(state, "messages", [])
            conversation_id = get_state_value(state, "conversation_id")

            if not messages:
                return {
                    "messages": [],
                    "pending_tools": [],
                    "error": "No messages provided",
                }

            start_time = get_state_value(state, "start_time")
            ttft_emitted = get_state_value(state, "ttft_emitted", False)
            loaded_toolsets = get_state_value(state, "loaded_toolsets", {"k8s": False})

            assistant_msgs, tool_calls, new_ttft_emitted = await run_model_turn(
                messages=messages,
                event_callback=self.event_callback,
                conversation_id=conversation_id,
                run_id=run_id,
                max_retries=3,
                tools_provider=self.tools_provider,
                loaded_toolsets=loaded_toolsets,
                start_time=start_time,
                ttft_emitted=ttft_emitted,
            )

            updated_state = {"messages": assistant_msgs, "pending_tools": []}
            if new_ttft_emitted:
                updated_state["ttft_emitted"] = True

            if tool_calls:
                updated_state["pending_tools"] = tool_calls

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
