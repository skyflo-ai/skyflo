"""LLM client service for OpenAI API interactions."""

from typing import Dict, Any, List, Optional, Callable, Awaitable, Type, Union
import logging
import json
import asyncio
import random
from dataclasses import dataclass
from datetime import datetime

from litellm import acompletion, get_supported_openai_params, supports_response_schema
from litellm.exceptions import RateLimitError
from openai.types.chat.chat_completion import Choice
from pydantic import BaseModel

from api.config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Response from LLM API."""

    choices: List[Choice]
    usage: Dict[str, int]
    model: str


class LLMClient:
    """Client for interacting with OpenAI's LLM API."""

    def __init__(
        self,
        api_key: str = None,
        model: str = "gpt-4o",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        provider: Optional[str] = None,
        max_retries: int = 3,
        initial_retry_delay: float = 5.0,
        exponential_base: float = 2.0,
    ):
        """Initialize the LLM client.

        Args:
            api_key: API key for the LLM provider
            model: Model to use for completions (can include provider prefix, e.g., "groq/llama-3")
            temperature: Temperature for response generation
            max_tokens: Maximum tokens in response
            provider: Provider prefix for litellm (optional, will be extracted from model if not provided)
            max_retries: Maximum number of retries for rate limit errors
            initial_retry_delay: Initial delay for retry in seconds
            exponential_base: Base for exponential backoff calculation
        """
        # Extract provider from model if it contains a slash
        if "/" in model and not provider:
            provider, model_name = model.split("/", 1)
            self.provider = provider
            self.model_name = model_name
        else:
            self.provider = provider or "openai"
            self.model_name = model

        # Auto-detect API key based on provider if not provided
        if not api_key:
            api_key = settings.get_api_key_for_provider(self.provider)

        self.api_key = api_key
        self.model = (
            f"{self.provider}/{self.model_name}"
            if not self.model_name.startswith(f"{self.provider}/")
            else self.model_name
        )
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay
        self.exponential_base = exponential_base

    def _model_supports_response_format(self) -> bool:
        """Check if the model supports response_format parameter.

        Returns:
            bool: True if response_format is supported, False otherwise
        """
        try:
            params = get_supported_openai_params(
                model=self.model_name, custom_llm_provider=self.provider
            )
            return "response_format" in params
        except Exception as e:
            logger.warning(f"Error checking response_format support: {str(e)}")
            return False

    def _model_supports_json_schema(self) -> bool:
        """Check if the model supports json_schema response format.

        Returns:
            bool: True if json_schema is supported, False otherwise
        """
        try:
            return supports_response_schema(
                model=self.model_name, custom_llm_provider=self.provider
            )
        except Exception as e:
            logger.warning(f"Error checking json_schema support: {str(e)}")
            return False

    async def _execute_with_retry(self, operation_func, *args, **kwargs):
        """Execute an operation with exponential backoff retry for rate limit errors.

        Args:
            operation_func: Async function to execute
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
            The result of the function call

        Raises:
            The last exception encountered if all retries fail
        """
        retry_count = 0

        while True:
            try:
                return await operation_func(*args, **kwargs)
            except RateLimitError as e:
                retry_count += 1

                if retry_count > self.max_retries:
                    logger.error(
                        f"Max retries ({self.max_retries}) exceeded for {self.provider} operation"
                    )
                    raise

                # Calculate backoff time using exponential backoff
                retry_delay = self.initial_retry_delay * (
                    self.exponential_base ** (retry_count - 1)
                )

                # Add jitter (between 80-120% of calculated delay)
                retry_delay = retry_delay * (0.8 + 0.4 * random.random())

                logger.warning(
                    f"Rate limit hit for {self.provider} model {self.model}. "
                    f"Retrying in {retry_delay:.2f}s (attempt {retry_count}/{self.max_retries})"
                )

                await asyncio.sleep(retry_delay)
            except Exception as e:
                # For non-rate-limit errors, don't retry
                logger.error(f"Error in {self.provider} operation: {str(e)}")
                raise

    async def _make_completion_call(
        self, messages, temperature=None, max_tokens=None, response_format=None, tools=None
    ):
        """Make a completion call to the LLM provider with common parameters.

        Args:
            messages: The messages to send to the LLM
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            response_format: Optional response format specification
            tools: Optional tools/functions for function calling

        Returns:
            The response from the LLM
        """
        return await acompletion(
            model=self.model,
            messages=messages,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens,
            api_key=self.api_key,
            response_format=response_format,
            tools=tools,
        )

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Get a chat completion from the LLM.

        Args:
            messages: List of messages for the conversation
            temperature: Optional override for temperature
            max_tokens: Optional override for max_tokens

        Returns:
            The text response from the LLM
        """
        try:
            # Log the request
            logger.debug(
                f"Sending chat completion request:\n"
                f"Model: {self.model}\n"
                f"Temperature: {temperature or self.temperature}\n"
                f"Max tokens: {max_tokens or self.max_tokens}\n"
                f"Messages: {json.dumps(messages, indent=2)}"
            )

            # Make the API call with retry
            response = await self._execute_with_retry(
                self._make_completion_call, messages, temperature, max_tokens
            )

            # Log the response
            logger.debug(
                f"Received chat completion response:\n"
                f"Usage: {response.usage}\n"
                f"Content: {response.choices[0].message.content if response.choices else 'No content'}"
            )

            # Return just the text content
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error in chat completion: {str(e)}")
            raise

    async def structured_chat_completion(
        self,
        messages: List[Dict[str, str]],
        schema: Union[Dict[str, Any], Type[BaseModel]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get a structured chat completion from the LLM using JSON schema.

        Args:
            messages: List of messages for the conversation
            schema: JSON schema or Pydantic model representing an OBJECT to format response
            temperature: Optional override for temperature
            max_tokens: Optional override for max_tokens

        Returns:
            The structured response from the LLM as a dict
        """
        try:
            # Check if the model supports structured output
            if not self._model_supports_response_format():
                raise ValueError(f"Model {self.model} does not support response_format parameter")

            # if not self._model_supports_json_schema():
            #     raise ValueError(f"Model {self.model} does not support json_schema formatting")

            # Generate a schema name (required by OpenAI)
            schema_name = "response_schema"
            if isinstance(schema, type) and hasattr(schema, "__name__"):
                schema_name = schema.__name__.lower()

            # Prepare response format parameter
            if isinstance(schema, type) and issubclass(schema, BaseModel):
                # Use the model's schema with additionalProperties=false
                json_schema_content = schema.model_json_schema()

                # Ensure additionalProperties is set to false for all object definitions
                for prop_name, prop_schema in json_schema_content.get("properties", {}).items():
                    if (
                        prop_schema.get("type") == "object"
                        and "additionalProperties" not in prop_schema
                    ):
                        prop_schema["additionalProperties"] = False

                # Also ensure it's set at the top level
                if "additionalProperties" not in json_schema_content:
                    json_schema_content["additionalProperties"] = False

                # Format according to OpenAI's requirements
                response_format = {
                    "type": "json_schema",
                    "json_schema": {"name": schema_name, "schema": json_schema_content},
                }
            else:
                # Direct schema provided - ensure additionalProperties is set
                if isinstance(schema, dict):
                    # Clone schema to avoid modifying the original
                    schema_copy = schema.copy()
                    if "additionalProperties" not in schema_copy:
                        schema_copy["additionalProperties"] = False

                    # Format according to OpenAI's requirements
                    response_format = {
                        "type": "json_schema",
                        "json_schema": {"name": schema_name, "schema": schema_copy},
                    }
                else:
                    # This case should be rare, but handle it just in case
                    response_format = {
                        "type": "json_schema",
                        "json_schema": {"name": schema_name, "schema": schema},
                    }

            # Log the request
            logger.debug(
                f"Sending structured chat completion request:\n"
                f"Model: {self.model}\n"
                f"Temperature: {temperature or self.temperature}\n"
                f"Max tokens: {max_tokens or self.max_tokens}\n"
                f"Schema: {response_format['json_schema']['schema']}\n"
                f"Messages: {json.dumps(messages, indent=2)}"
            )

            # Make the API call with retry
            response = await self._execute_with_retry(
                self._make_completion_call, messages, temperature, max_tokens, response_format
            )

            # Log the response
            logger.debug(
                f"Received structured chat completion response:\n"
                f"Usage: {response.usage}\n"
                f"Content: {response.choices[0].message.content if response.choices else 'No content'}"
            )

            # Parse the response based on the output type
            if response.choices and response.choices[0].message.content:
                content = response.choices[0].message.content
                result = None

                # Handle different response types
                if isinstance(content, dict):
                    # Some models might return a parsed dict directly
                    result = content
                elif isinstance(content, str):
                    try:
                        # Parse JSON response
                        result = json.loads(content)
                    except json.JSONDecodeError as e:
                        logger.error(f"Error parsing JSON response: {str(e)}")
                        raise ValueError(f"LLM returned invalid JSON: {content}")
                else:
                    raise ValueError(f"Unexpected response format: {type(content)}")

                # Ensure we're returning a dictionary
                if not isinstance(result, dict):
                    raise ValueError(f"Expected dict response, got: {type(result)}")

                return result
            else:
                raise ValueError("LLM response contained no content")

        except Exception as e:
            logger.error(f"Error in structured chat completion: {str(e)}")
            raise

    async def function_call(
        self,
        messages: List[Dict[str, str]],
        functions: List[Dict[str, Any]],
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Make a function call using the LLM.

        Args:
            messages: List of messages for the conversation
            functions: List of function definitions
            temperature: Optional override for temperature

        Returns:
            Dictionary containing the function call details
        """
        try:
            # Log the request
            logger.debug(
                f"Sending function call request:\n"
                f"Model: {self.model}\n"
                f"Temperature: {temperature or self.temperature}\n"
                f"Functions: {json.dumps(functions, indent=2)}\n"
                f"Messages: {json.dumps(messages, indent=2)}"
            )

            # Make the API call with retry
            response = await self._execute_with_retry(
                self._make_completion_call, messages, temperature, None, None, functions
            )

            # Log the response
            logger.debug(
                f"Received function call response:\n"
                f"Usage: {response.usage}\n"
                f"Function call: {response.choices[0].message.tool_calls if response.choices else 'No function call'}"
            )

            # Return the function call details
            if response.choices and response.choices[0].message.tool_calls:
                tool_call = response.choices[0].message.tool_calls[0]
                return {
                    "name": tool_call.function.name,
                    "arguments": json.loads(tool_call.function.arguments),
                }
            else:
                return {"name": None, "arguments": None}

        except Exception as e:
            logger.error(f"Error in function call: {str(e)}")
            raise

    async def summarize_execution_context(
        self,
        user_query: str,
        execution_context: Dict[str, Any],
        max_tokens: int = 20000,
        event_callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Intelligently summarize execution context based on user query relevance.

        Args:
            user_query: The original user query to provide focus for summarization
            execution_context: The full execution context to be summarized
            max_tokens: Target maximum token count for the summarized context
            event_callback: Optional callback for real-time event updates
            conversation_id: Optional conversation ID for context

        Returns:
            A summarized version of the execution context
        """
        try:
            # Calculate approximate tokens (rough estimate: 4 chars ~= 1 token)
            context_str = json.dumps(execution_context)
            approx_tokens = len(context_str) // 4

            # If context is already under limit, return it as is
            if approx_tokens <= max_tokens:
                logger.debug(
                    f"Context already under token limit ({approx_tokens} tokens), no summarization needed"
                )
                return execution_context

            logger.debug(
                f"Context size exceeds token limit ({approx_tokens} tokens), summarizing..."
            )

            # Emit event that we're starting summarization
            if event_callback:
                await event_callback(
                    {
                        "type": "summarization_started",
                        "agent": "response_generator",
                        "message": "Summarizing execution context for final response generation",
                        "phase": "responding",
                        "state": "summarize",
                        "conversation_id": conversation_id,
                        "details": {
                            "token_count": approx_tokens,
                            "max_tokens": max_tokens,
                            "query": (
                                user_query[:100] + "..." if len(user_query) > 100 else user_query
                            ),
                            "timestamp": datetime.now().isoformat(),
                            "conversation_id": conversation_id,
                        },
                        "data": {
                            "progress": 0.85,
                            "message": "Preparing response by summarizing execution context",
                            "conversation_id": conversation_id,
                        },
                    }
                )

            # Prepare the summarization prompt
            summarization_prompt = [
                {
                    "role": "system",
                    "content": """You are an AI specialized in summarizing execution data from Kubernetes operations.
Your task is to analyze the execution context and create a comprehensive summary of the most relevant information.

Guidelines:
1. Focus on information most relevant to the user's original query
2. Preserve exact command outputs for important operations
3. Maintain the structure of key data points (step IDs, tool names, etc.)
4. Include all verification results and their details
5. For large outputs, extract the most important lines/information
6. Summarize in a structured format that maintains data relationships
7. Ensure critical error messages are preserved verbatim
8. Return the summary as a JSON structure that maintains the essential hierarchy of the original""",
                },
                {
                    "role": "user",
                    "content": f"""Original user query: {user_query}
                    
Execution context to summarize:
{json.dumps(execution_context, indent=2)}

Create a comprehensive summary of this execution context, focusing on information most relevant to the user's query.
Return ONLY the JSON data structure of the summarized context without any explanations or markdown formatting.""",
                },
            ]

            # Make the summarization API call with retry
            response = await self._execute_with_retry(
                self._make_completion_call,
                summarization_prompt,
                0.1,  # Low temperature for consistent summaries
                None,
                {"type": "json_object"},
            )

            # Extract and parse the summary
            summary_text = response.choices[0].message.content
            try:
                summarized_context = json.loads(summary_text)
                summarized_tokens = len(json.dumps(summarized_context)) // 4
                logger.debug(
                    f"Successfully summarized context from {approx_tokens} tokens to approximately {summarized_tokens} tokens"
                )

                # Emit event for successful summarization
                if event_callback:
                    await event_callback(
                        {
                            "type": "summarization_completed",
                            "agent": "response_generator",
                            "message": "Execution context summarization completed successfully",
                            "phase": "responding",
                            "state": "summarize",
                            "conversation_id": conversation_id,
                            "details": {
                                "original_tokens": approx_tokens,
                                "summarized_tokens": summarized_tokens,
                                "reduction_percentage": (
                                    round((1 - (summarized_tokens / approx_tokens)) * 100, 2)
                                    if approx_tokens > 0
                                    else 0
                                ),
                                "timestamp": datetime.now().isoformat(),
                                "conversation_id": conversation_id,
                            },
                            "data": {
                                "progress": 0.90,
                                "message": "Context summarized, proceeding to final response generation",
                                "conversation_id": conversation_id,
                            },
                        }
                    )

                return summarized_context
            except json.JSONDecodeError:
                logger.error(
                    "Failed to parse summarized context as JSON, using fallback summarization"
                )

                # Emit event for summarization failure
                if event_callback:
                    await event_callback(
                        {
                            "type": "summarization_error",
                            "agent": "response_generator",
                            "message": "Failed to parse summarized context as JSON, using fallback method",
                            "phase": "responding",
                            "state": "summarize",
                            "conversation_id": conversation_id,
                            "details": {
                                "error": "JSON parse error",
                                "timestamp": datetime.now().isoformat(),
                                "conversation_id": conversation_id,
                            },
                            "data": {
                                "progress": 0.85,
                                "message": "Using fallback summarization method",
                                "conversation_id": conversation_id,
                            },
                        }
                    )

                # Fallback: extract what looks like JSON
                if "{" in summary_text and "}" in summary_text:
                    json_start = summary_text.find("{")
                    json_end = summary_text.rfind("}") + 1
                    cleaned_json = summary_text[json_start:json_end]
                    try:
                        return json.loads(cleaned_json)
                    except:
                        pass

                # If all else fails, use the original truncation method as backup
                return self._fallback_summarize(execution_context)

        except Exception as e:
            logger.error(f"Error during context summarization: {str(e)}")

            # Emit event for summarization error
            if event_callback:
                await event_callback(
                    {
                        "type": "summarization_error",
                        "agent": "response_generator",
                        "message": f"Error during context summarization: {str(e)}",
                        "phase": "responding",
                        "state": "summarize",
                        "conversation_id": conversation_id,
                        "details": {
                            "error": str(e),
                            "timestamp": datetime.now().isoformat(),
                            "conversation_id": conversation_id,
                        },
                        "data": {
                            "progress": 0.85,
                            "message": "Using fallback summarization method due to error",
                            "conversation_id": conversation_id,
                        },
                    }
                )

            # In case of failure, use a simpler fallback method
            return self._fallback_summarize(execution_context)

    def _fallback_summarize(self, data: Dict[str, Any], max_depth: int = 3) -> Dict[str, Any]:
        """Fallback method for summarizing data when the LLM-based summary fails.

        Args:
            data: The data to summarize
            max_depth: Maximum recursion depth

        Returns:
            Summarized data
        """
        if max_depth <= 0:
            if isinstance(data, dict) and len(data) > 5:
                keys = list(data.keys())
                return {
                    **{k: data[k] for k in keys[:3]},  # Keep first 3 items
                    "_summary": f"[Truncated {len(data) - 3} more items]",
                }
            elif isinstance(data, list) and len(data) > 5:
                return data[:3] + [f"[Truncated {len(data) - 3} more items]"]
            else:
                return data

        if isinstance(data, dict):
            result = {}
            # Process most important keys first (status, error, verification, etc.)
            priority_keys = [
                "status",
                "error",
                "verification_result",
                "validation_results",
                "intent",
                "steps_executed",
                "tool",
                "action",
                "output",
            ]

            # First process priority keys
            for key in [k for k in priority_keys if k in data]:
                value = data[key]
                if isinstance(value, (dict, list)):
                    result[key] = self._fallback_summarize(value, max_depth - 1)
                elif isinstance(value, str) and len(value) > 1000:
                    result[key] = value[:500] + "... [truncated]"
                else:
                    result[key] = value

            # Then process remaining keys
            remaining_keys = [k for k in data.keys() if k not in priority_keys]
            for key in remaining_keys[:10]:  # Limit to first 10 non-priority keys
                value = data[key]
                if isinstance(value, (dict, list)):
                    result[key] = self._fallback_summarize(value, max_depth - 1)
                elif isinstance(value, str) and len(value) > 1000:
                    result[key] = value[:500] + "... [truncated]"
                else:
                    result[key] = value

            # Add a count of omitted keys if necessary
            if len(remaining_keys) > 10:
                result["_omitted"] = f"[Truncated {len(remaining_keys) - 10} more keys]"

            return result

        elif isinstance(data, list):
            if len(data) > 10:
                processed = [
                    (
                        self._fallback_summarize(item, max_depth - 1)
                        if isinstance(item, (dict, list))
                        else item
                    )
                    for item in data[:10]
                ]
                processed.append(f"[Truncated {len(data) - 10} more items]")
                return processed
            else:
                return [
                    (
                        self._fallback_summarize(item, max_depth - 1)
                        if isinstance(item, (dict, list))
                        else item
                    )
                    for item in data
                ]
        else:
            return data
