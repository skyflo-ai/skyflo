"""Utility functions for tool operations."""

import json
import yaml
import tempfile
import os
import tiktoken
from typing import Dict, Any, Optional, Union, List
from datetime import datetime
from ..common.models import ToolResponse, ResourceIdentifier


def create_tool_response(
    tool: str,
    command: str,
    result: Optional[Any] = None,
    error: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> ToolResponse:
    """Create a standardized tool response.

    Args:
        tool: Name of the tool
        command: Executed command
        result: Command result
        error: Error message if any
        metadata: Additional metadata

    Returns:
        ToolResponse object
    """
    return ToolResponse(
        tool=tool,
        command=command,
        status="error" if error else "success",
        result=result,
        error=error,
        timestamp=datetime.now(),
        metadata=metadata or {},
    )


def parse_resource_identifier(resource_str: str) -> ResourceIdentifier:
    """Parse a resource identifier string.

    Args:
        resource_str: String in format [kind]/[name] or [kind]/[name].[namespace]

    Returns:
        ResourceIdentifier object
    """
    parts = resource_str.split("/")
    if len(parts) != 2:
        raise ValueError(f"Invalid resource identifier: {resource_str}")

    kind = parts[0]
    name_parts = parts[1].split(".")

    return ResourceIdentifier(
        kind=kind,
        name=name_parts[0],
        namespace=name_parts[1] if len(name_parts) > 1 else None,
        api_version="v1",  # Default, can be overridden
    )


def format_command_output(output: Union[str, Dict[str, Any]]) -> str:
    """Format command output for consistent display.

    Args:
        output: Command output (string or dict)

    Returns:
        Formatted string
    """
    if isinstance(output, dict):
        return json.dumps(output, indent=2)
    return str(output)


def validate_namespace(namespace: Optional[str] = None) -> str:
    """Validate and return namespace, using default if none provided.

    Args:
        namespace: Optional namespace name

    Returns:
        Validated namespace name
    """
    if not namespace:
        return "default"
    return namespace


def parse_label_selector(labels: Dict[str, str]) -> str:
    """Convert label dictionary to selector string.

    Args:
        labels: Dictionary of labels

    Returns:
        Label selector string
    """
    return ",".join(f"{k}={v}" for k, v in labels.items())


def parse_command_args(args: Dict[str, Any]) -> str:
    """Convert command arguments to string format.

    Args:
        args: Dictionary of command arguments

    Returns:
        Formatted command string
    """
    parts = []
    for key, value in args.items():
        if isinstance(value, bool):
            if value:
                parts.append(f"--{key}")
        else:
            parts.append(f"--{key}={value}")
    return " ".join(parts)


def create_yaml_file(data: Dict[str, Any], prefix: str = "values") -> str:
    """Create a temporary YAML file from a dictionary.

    Args:
        data: The data to write to the YAML file
        prefix: Prefix for the temporary file name

    Returns:
        Path to the created temporary file
    """
    fd, temp_path = tempfile.mkstemp(prefix=f"{prefix}_", suffix=".yaml")
    try:
        with os.fdopen(fd, "w") as f:
            yaml.dump(data, f, default_flow_style=False)
        return temp_path
    except Exception as e:
        # Ensure the file is deleted if there's an error
        try:
            os.unlink(temp_path)
        except:
            pass
        raise e


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """Count the number of tokens in a text using tiktoken.

    Args:
        text: Text to count tokens for
        model: Model name to use for token counting

    Returns:
        Number of tokens
    """
    # Get the encoding for the specified model
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # Fall back to cl100k_base encoding if model not found
        encoding = tiktoken.get_encoding("cl100k_base")

    # Count tokens
    tokens = encoding.encode(text)
    return len(tokens)


def count_message_tokens(messages: List[Dict[str, Any]], model: str = "gpt-4") -> int:
    """Count tokens in a list of chat messages.

    Args:
        messages: List of message dictionaries
        model: Model name for token counting

    Returns:
        Total token count
    """
    total_tokens = 0
    for message in messages:
        # Count tokens in the message content
        if "content" in message and message["content"]:
            total_tokens += count_tokens(message["content"], model)

        # Count tokens in function calls if present
        if "function_call" in message and isinstance(message["function_call"], dict):
            func_call = message["function_call"]
            if "name" in func_call:
                total_tokens += count_tokens(func_call["name"], model)
            if "arguments" in func_call:
                total_tokens += count_tokens(func_call["arguments"], model)

        # Add tokens for message formatting (role, etc.)
        total_tokens += 4  # Approximate overhead per message

    # Add tokens for chat formatting
    total_tokens += 3  # Approximate overhead for the entire conversation

    return total_tokens


def apply_sliding_window(
    messages: List[Dict[str, Any]], max_tokens: int, model: str = "gpt-4"
) -> List[Dict[str, Any]]:
    """Apply sliding window to messages to keep context within token limit.

    Args:
        messages: List of message dictionaries
        max_tokens: Maximum number of tokens to keep
        model: Model name for token counting

    Returns:
        Trimmed list of messages
    """
    # If messages are empty, return empty list
    if not messages:
        return []

    # Always keep the system message if present
    system_messages = []
    other_messages = []

    for message in messages:
        if message.get("role") == "system":
            system_messages.append(message)
        else:
            other_messages.append(message)

    # Start with most recent messages and work backwards
    other_messages.reverse()

    # Initialize with system messages
    result_messages = system_messages.copy()
    current_tokens = count_message_tokens(result_messages, model)

    # Add as many recent messages as possible
    for message in other_messages:
        message_tokens = count_message_tokens([message], model)

        # If adding this message would exceed the limit, stop
        if current_tokens + message_tokens > max_tokens:
            break

        result_messages.append(message)
        current_tokens += message_tokens

    # Restore original order (system messages first, then chronological)
    result_messages = system_messages + [
        m for m in result_messages if m not in system_messages
    ]

    return result_messages


def clear_conversation_history(
    reason: str = "Starting new conversation",
) -> Dict[str, Any]:
    """Create a tool response for clearing conversation history.

    Args:
        reason: Reason for clearing history

    Returns:
        Tool response indicating history was cleared
    """
    return create_tool_response(
        tool="conversation_manager",
        command="clear_history",
        result="Conversation history cleared successfully.",
        metadata={"reason": reason},
    )
