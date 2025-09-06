"""Utility functions for the API."""

import logging
from typing import Any, Optional
from decouple import config, UndefinedValueError


logger = logging.getLogger(__name__)


def get_state_value(state: Any, key: str, default: Any = None) -> Any:
    if hasattr(state, key):
        return getattr(state, key, default)
    elif hasattr(state, "get"):
        return state.get(key, default)
    else:
        return default


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
        api_key = config(env_var_name, default=None)
        if api_key:
            return api_key
        else:
            logger.warning(f"Environment variable {env_var_name} is set but empty.")
            return None
    except UndefinedValueError:
        logger.warning(
            f"API key environment variable {env_var_name} not found for provider '{provider}'."
        )
        return None
    except Exception as e:
        logger.error(f"Error fetching API key for provider {provider}: {e}")
        return None
