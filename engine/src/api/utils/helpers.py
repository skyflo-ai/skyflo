"""Utility functions for the API."""

import logging
import time
import os
import re
from typing import Dict, Any, List, Optional
from decouple import config, UndefinedValueError

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


def normalize_step_parameters(step: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize the 'parameters' field within a single plan step.

    Converts parameters from the list format [{"name": "key", "value": "val"}]
    to the dictionary format {"key": "val"}.

    If the parameters are already a dictionary or not present, the step is returned unchanged.

    Args:
        step: A dictionary representing a single step in a plan.

    Returns:
        The step dictionary with normalized parameters, or the original step if no normalization is needed.
    """
    parameters = step.get("parameters")

    if isinstance(parameters, list):
        try:
            normalized_params = {
                param.get("name"): param.get("value")
                for param in parameters
                if isinstance(param, dict) and "name" in param  # Ensure 'name' key exists
            }
            # Create a copy of the step to avoid modifying the original dict in place
            normalized_step = step.copy()
            normalized_step["parameters"] = normalized_params
            return normalized_step
        except Exception as e:
            logger.error(
                f"Error normalizing parameters for step {step.get('step_id', 'unknown')}: {e}"
            )
            # Return the original step if normalization fails
            return step
    # If parameters are already a dict or None/missing, return the step as is
    elif isinstance(parameters, dict) or parameters is None:
        return step
    else:
        logger.warning(
            f"Unexpected type for parameters in step {step.get('step_id', 'unknown')}: {type(parameters)}. Skipping normalization."
        )
        return step


def normalize_steps_list(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalize the parameters for all steps in a list.

    Applies normalize_step_parameters to each step in the list.

    Args:
        steps: A list of step dictionaries.

    Returns:
        A new list containing steps with normalized parameters.
    """
    return [normalize_step_parameters(step) for step in steps]


def get_api_key_for_provider(provider: str) -> Optional[str]:
    """Get API key for a specific LLM provider from environment variables.

    Args:
        provider: Provider name (e.g., 'openai', 'groq'). Case-insensitive.

    Returns:
        API key for the provider if found, otherwise None.
    """
    provider = provider.strip().upper()
    env_var_name = f"{provider}_API_KEY"
    try:
        # Use default=None to return None if the variable is not set
        api_key = config(env_var_name, default=None)
        if api_key:
            logger.debug(f"Found API key for provider '{provider}' via env var {env_var_name}")
            return api_key
        else:
            logger.warning(f"Environment variable {env_var_name} is set but empty.")
            return None
    except UndefinedValueError:
        logger.warning(f"API key environment variable {env_var_name} not found for provider '{provider}'.")
        return None
    except Exception as e:
        logger.error(f"Error fetching API key for provider {provider}: {e}")
        return None


## move get_api_key_for_provider to helper file no logic in settings
## remove python-dotenv package
