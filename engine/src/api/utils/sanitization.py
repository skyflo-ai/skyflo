import logging
from typing import Any, Dict, List

from ..agent.prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def prepare_messages_with_system_prompt(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    has_system_message = any(msg.get("role") == "system" for msg in messages)

    if not has_system_message:
        system_message = {"role": "system", "content": SYSTEM_PROMPT}
        return [system_message] + messages

    return messages


def mcp_tools_to_openai_format(tools_response: Dict[str, Any]) -> List[Dict[str, Any]]:
    tools = []

    if not isinstance(tools_response, dict) or "tools" not in tools_response:
        return tools

    for tool in tools_response["tools"]:
        if not isinstance(tool, dict):
            continue

        input_schema = tool.get("input_schema") or tool.get("inputSchema") or None

        tool_definition = {
            "type": "function",
            "function": {
                "name": tool.get("name", ""),
                "description": tool.get("description", ""),
                "parameters": (
                    input_schema
                    if isinstance(input_schema, dict)
                    else {"type": "object", "properties": {}, "required": []}
                ),
            },
        }

        if not input_schema and "parameters" in tool and isinstance(tool["parameters"], list):
            for param in tool["parameters"]:
                if not isinstance(param, dict):
                    continue

                param_name = param.get("name")
                if not param_name:
                    continue

                param_def = {
                    "type": param.get("type", "string"),
                    "description": param.get("description", ""),
                }

                tool_definition["function"]["parameters"]["properties"][param_name] = param_def

                if param.get("required", False):
                    required_list = tool_definition["function"]["parameters"].setdefault(
                        "required", []
                    )
                    required_list.append(param_name)

        tools.append(tool_definition)

    return tools


def sanitize_messages_for_openai(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    sanitized: List[Dict[str, Any]] = []

    # Track which tool_call_ids have valid immediate responses
    valid_tool_call_ids = set()
    for i, msg in enumerate(messages):
        if not isinstance(msg, dict):
            continue

        if msg.get("role") == "assistant" and isinstance(msg.get("tool_calls"), list):
            expected_tool_ids = {
                tc.get("id") for tc in msg["tool_calls"] if isinstance(tc, dict) and tc.get("id")
            }
            found_tool_ids = set()

            j = i + 1
            while j < len(messages) and messages[j].get("role") == "tool":
                tool_msg = messages[j]
                tc_id = tool_msg.get("tool_call_id")
                if tc_id in expected_tool_ids:
                    found_tool_ids.add(tc_id)
                j += 1

            valid_tool_call_ids.update(found_tool_ids)

    seen_tool_call_ids = set()

    for msg in messages:
        if not isinstance(msg, dict):
            continue

        role = msg.get("role")
        content = msg.get("content")

        if content is None:
            msg = {**msg, "content": ""}

        if role == "assistant" and isinstance(msg.get("tool_calls"), list):
            valid_tool_calls = []
            for tool_call in msg["tool_calls"]:
                if isinstance(tool_call, dict):
                    tc_id = tool_call.get("id")
                    if tc_id:
                        if tc_id in valid_tool_call_ids:
                            seen_tool_call_ids.add(tc_id)
                            valid_tool_calls.append(tool_call)

            if valid_tool_calls:
                msg = {**msg, "tool_calls": valid_tool_calls}
            else:
                msg = {k: v for k, v in msg.items() if k != "tool_calls"}

        if role == "tool":
            tc_id = msg.get("tool_call_id")
            if not tc_id or tc_id not in seen_tool_call_ids:
                continue

        sanitized.append(msg)

    return sanitized


def _sanitize_schema_for_gemini(schema: Any) -> Any:
    if not isinstance(schema, dict):
        return schema

    sanitized = dict(schema)

    for combinator in ("anyOf", "oneOf", "allOf"):
        if (
            combinator in sanitized
            and isinstance(sanitized[combinator], list)
            and sanitized[combinator]
        ):
            options = [opt for opt in sanitized[combinator] if isinstance(opt, dict)]
            chosen = next(
                (opt for opt in options if opt.get("type") != "null"), options[0] if options else {}
            )
            parent_description = sanitized.get("description")
            parent_default = sanitized.get("default")
            sanitized = {**sanitized, **chosen}
            sanitized.pop(combinator, None)
            if parent_description and "description" not in sanitized:
                sanitized["description"] = parent_description
            if parent_default is not None and "default" not in sanitized:
                sanitized["default"] = parent_default

    sanitized.pop("additionalProperties", None)
    sanitized.pop("nullable", None)

    if isinstance(sanitized.get("properties"), dict):
        sanitized["properties"] = {
            key: _sanitize_schema_for_gemini(value)
            for key, value in sanitized["properties"].items()
        }

    if "items" in sanitized:
        sanitized["items"] = _sanitize_schema_for_gemini(sanitized["items"])

    if "type" not in sanitized:
        sanitized["type"] = "string"

    if "required" in sanitized and not isinstance(sanitized["required"], list):
        sanitized["required"] = []

    return sanitized


def sanitize_messages_for_gemini(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(tools, list):
        return []

    sanitized_tools: List[Dict[str, Any]] = []
    for tool in tools:
        try:
            if not isinstance(tool, dict) or tool.get("type") != "function":
                continue
            function_def = tool.get("function", {})
            params = function_def.get("parameters")
            if isinstance(params, dict):
                function_def["parameters"] = _sanitize_schema_for_gemini(params)
            sanitized_tools.append({"type": "function", "function": function_def})
        except Exception:
            sanitized_tools.append(tool)

    return sanitized_tools
