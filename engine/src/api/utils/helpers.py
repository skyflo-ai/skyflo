"""Utility functions for the API."""

import logging
import time
from typing import Dict, Any, List

import tiktoken

logger = logging.getLogger(__name__)


def get_timestamp() -> float:
    """Get the current timestamp.

    Returns:
        Current timestamp as a float
    """
    return time.time()


def count_message_tokens(messages: List[Dict[str, Any]], model: str = "gpt-4o") -> int:
    """Count the number of tokens in a list of messages.

    Args:
        messages: List of messages (dict with 'role' and 'content')
        model: Model name to use for token counting

    Returns:
        Number of tokens in the messages
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        logger.warning(f"Model {model} not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")

    # Count tokens for each message
    tokens_per_message = 3  # Every message follows format: <|start|>{role/name}\n{content}<|end|>\n
    tokens_per_name = 1  # If there's a name, the role is omitted

    total_tokens = 0
    for message in messages:
        total_tokens += tokens_per_message
        for key, value in message.items():
            if key == "role":
                # Role is always required and is 1 token
                continue
            elif key == "content":
                if value is not None:  # Content can be None for function calls
                    total_tokens += len(encoding.encode(str(value)))
            else:
                total_tokens += len(encoding.encode(str(key))) + len(encoding.encode(str(value)))
                total_tokens += tokens_per_name  # For the name

    total_tokens += 3  # Every reply is primed with <|start|>assistant<|message|>

    return total_tokens


def apply_sliding_window(
    messages: List[Dict[str, Any]], max_tokens: int, model: str = "gpt-4o"
) -> List[Dict[str, Any]]:
    """Apply sliding window to messages to limit token count.

    This keeps the first system message and the most recent messages that fit
    within the token limit.

    Args:
        messages: List of messages (dict with 'role' and 'content')
        max_tokens: Maximum number of tokens to allow
        model: Model name to use for token counting

    Returns:
        List of messages within the token limit
    """
    if not messages:
        return []

    # Always keep the system message if present
    if messages[0].get("role") == "system":
        system_message = [messages[0]]
        user_messages = messages[1:]
    else:
        system_message = []
        user_messages = messages

    # Calculate tokens for system message if present
    system_tokens = count_message_tokens(system_message, model) if system_message else 0
    available_tokens = max_tokens - system_tokens

    # Apply sliding window starting from the most recent message
    result = []
    current_tokens = 0

    # Process messages in reverse order (newest first)
    for msg in reversed(user_messages):
        msg_tokens = count_message_tokens([msg], model)

        if current_tokens + msg_tokens <= available_tokens:
            result.insert(0, msg)  # Insert at the beginning to maintain order
            current_tokens += msg_tokens
        else:
            break

    # Add system message back at the beginning
    if system_message:
        result = system_message + result

    logger.debug(
        f"Applied sliding window: {len(messages)} messages -> {len(result)} messages, "
        f"{count_message_tokens(messages, model)} tokens -> {count_message_tokens(result, model)} tokens"
    )

    # If we couldn't fit even a single message, include at least the most recent one
    if not result or (not system_message and len(result) == 0):
        if system_message:
            return system_message + [user_messages[-1]]
        else:
            return [user_messages[-1]]

    return result


def clear_conversation_history(reason: str) -> Dict[str, Any]:
    """Create a standardized response for clearing conversation history.

    Args:
        reason: Reason for clearing history

    Returns:
        Dict containing the result
    """
    logger.debug(f"Clearing conversation history: {reason}")
    return {
        "status": "success",
        "action": "clear_conversation_history",
        "reason": reason,
        "timestamp": get_timestamp(),
    }
