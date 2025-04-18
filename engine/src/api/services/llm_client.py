"""LLM client service for OpenAI API interactions."""

from typing import Dict, Any, List, Optional, Callable, Awaitable
import logging
import json
from dataclasses import dataclass
from datetime import datetime

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice

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
        api_key: str,
        model: str = "gpt-4-turbo-preview",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ):
        """Initialize the LLM client.

        Args:
            api_key: OpenAI API key
            model: Model to use for completions
            temperature: Temperature for response generation
            max_tokens: Maximum tokens in response
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

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

            # Make the API call
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
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

            # Make the API call
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                functions=functions,
                temperature=temperature or self.temperature,
            )

            # Log the response
            logger.debug(
                f"Received function call response:\n"
                f"Usage: {response.usage}\n"
                f"Function call: {response.choices[0].message.function_call if response.choices else 'No function call'}"
            )

            # Return the function call details
            if response.choices and response.choices[0].message.function_call:
                return {
                    "name": response.choices[0].message.function_call.name,
                    "arguments": json.loads(response.choices[0].message.function_call.arguments),
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

            # Make the summarization API call
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=summarization_prompt,
                temperature=0.1,  # Low temperature for consistent summaries
                response_format={"type": "json_object"},
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
