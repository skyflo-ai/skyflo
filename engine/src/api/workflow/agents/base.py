"""Base agent class for Skyflo.ai API workflow."""

from typing import Dict, Any, Optional, AsyncGenerator, List, Mapping, Sequence, Type, Union
from pydantic import BaseModel, Field
import logging

from autogen_agentchat.base import Response
from autogen_agentchat.messages import (
    AgentEvent,
    ChatMessage,
    TextMessage,
)
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.state import BaseState
from autogen_core import (
    CancellationToken,
    ComponentBase,
    ComponentModel,
)
from autogen_core.model_context import ChatCompletionContext

from api.config import settings
from ...services.llm_client import LLMClient

logger = logging.getLogger(__name__)


class BaseAgentState(BaseState):
    """State for base agent."""

    inner_state: Mapping[str, Any] = Field(default_factory=dict)
    type: str = Field(default="BaseAgentState")


class BaseAgentConfig(BaseModel):
    """The declarative configuration for a BaseAgent."""

    name: str
    system_message: str
    model_context: ComponentModel | None = None
    description: str | None = None


class BaseAgent(ComponentBase):
    """Base class for all Skyflo agents."""

    component_type = "skyflo.agents.BaseAgent"
    component_config_schema = BaseAgentConfig
    component_provider_override = "skyflo.agents.BaseAgent"

    def __init__(
        self,
        name: str,
        system_message: str,
        model_context: Optional[ChatCompletionContext] = None,
        description: Optional[str] = None,
    ) -> None:
        """Initialize the base agent.

        Args:
            name: Name of the agent
            system_message: System message for the agent
            model_context: Model context for the agent
            description: Description of the agent
        """
        self.name = name
        self.system_message = system_message
        self.model_context = model_context
        self.description = description or "Base Skyflo agent"
        self.config = settings
        self.llm_client = LLMClient(
            model=settings.LLM_MODEL,
        )
        # Event callback for real-time updates
        self.event_callback = None

        # Import here to avoid circular import
        from autogen_ext.models.openai import OpenAIChatCompletionClient

        # Create the model client
        model_client = OpenAIChatCompletionClient(
            model=self.config.MODEL_NAME,
            api_key=self.config.OPENAI_API_KEY,
            temperature=self.config.TEMPERATURE,
        )

        if self.config.AGENT_TYPE == "assistant":
            self.agent = AssistantAgent(
                name=name,
                system_message=system_message,
                model_client=model_client,
                model_context=model_context,
                description=description or "Base Skyflo agent",
            )
        else:
            self.agent = UserProxyAgent(
                name=name,
                system_message=system_message,
                human_input_mode="NEVER",
            )

    @property
    def produced_message_types(self) -> Sequence[type[ChatMessage]]:
        return (TextMessage,)

    async def on_messages(
        self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken
    ) -> Response:
        """Process incoming messages and return a response."""
        response: Response | None = None
        async for msg in self.on_messages_stream(messages, cancellation_token):
            if isinstance(msg, Response):
                response = msg

        assert response is not None
        return response

    async def on_messages_stream(
        self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken
    ) -> AsyncGenerator[AgentEvent | ChatMessage | Response, None]:
        """Stream processing of messages."""
        raise NotImplementedError("Subclasses must implement on_messages_stream")

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        """Reset agent state."""
        pass

    async def save_state(self) -> Mapping[str, Any]:
        """Save agent state."""
        state = BaseAgentState(
            inner_state={
                "name": self.name,
                "system_message": self.system_message,
                "description": self.description,
            }
        )
        return state.model_dump()

    async def load_state(self, state: Mapping[str, Any]) -> None:
        """Load agent state."""
        agent_state = BaseAgentState.model_validate(state)
        inner_state = agent_state.inner_state
        self.name = inner_state.get("name", self.name)
        self.system_message = inner_state.get("system_message", self.system_message)
        self.description = inner_state.get("description", self.description)

    def _to_config(self) -> BaseAgentConfig:
        """Convert agent to config."""
        return BaseAgentConfig(
            name=self.name,
            system_message=self.system_message,
            model_context=(self.model_context.dump_component() if self.model_context else None),
            description=self.description,
        )

    @classmethod
    def _from_config(cls, config: BaseAgentConfig):
        """Create agent from config."""
        model_context = (
            ChatCompletionContext.load_component(config.model_context)
            if config.model_context is not None
            else None
        )
        return cls(
            name=config.name,
            system_message=config.system_message,
            model_context=model_context,
            description=config.description,
        )

    async def send(self, message: Dict[str, Any], recipient: Optional["BaseAgent"] = None) -> None:
        """Send a message to another agent.

        Args:
            message: Message to send
            recipient: Recipient agent (if None, broadcasts to all)
        """
        if recipient:
            await self.agent.send(message, recipient.agent)
        else:
            # Broadcast implementation will be added later
            pass

    async def receive(self) -> Dict[str, Any]:
        """Receive a message from another agent."""
        return await self.agent.receive()

    def apply_sliding_window_to_messages(
        self, messages: List[Dict[str, Any]], window_size: int = 10
    ) -> List[Dict[str, Any]]:
        """Apply sliding window to message history.

        Args:
            messages: List of messages
            window_size: Size of the sliding window

        Returns:
            List of messages within the window
        """
        # Always keep the system message
        system_message = messages[0] if messages and messages[0]["role"] == "system" else None

        # Apply window to the rest
        windowed_messages = messages[-window_size:] if len(messages) > window_size else messages

        # Add system message back if it exists
        if system_message and windowed_messages[0] != system_message:
            windowed_messages = [system_message] + windowed_messages

        return windowed_messages

    def check_token_count(self, messages: List[Dict[str, Any]]) -> int:
        """Check the token count of messages.

        Args:
            messages: List of chat messages

        Returns:
            Token count of messages
        """
        from ...utils.helpers import count_message_tokens

        return count_message_tokens(messages, self.config.MODEL_NAME)

    async def _get_llm_response(
        self, messages: List[Dict[str, Any]], temperature: float = 0.2
    ) -> str:
        """Get response from the LLM.

        Args:
            messages: List of messages to send to the LLM
            temperature: Optional temperature override

        Returns:
            LLM response text
        """
        try:
            # The chat_completion method now returns the text content directly
            return await self.llm_client.chat_completion(messages=messages, temperature=temperature)
        except Exception as e:
            logger.error(f"Error getting LLM response: {str(e)}")
            raise

    async def _get_structured_llm_response(
        self,
        messages: List[Dict[str, Any]],
        schema: Union[Dict[str, Any], Type[BaseModel]],
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        """Get structured response from the LLM using a schema.

        Args:
            messages: List of messages to send to the LLM
            schema: JSON schema or Pydantic model to format the response
            temperature: Optional temperature override

        Returns:
            Structured response as a dictionary
        """
        try:
            # Use structured_chat_completion to get a formatted response
            raw = await self.llm_client.structured_chat_completion(
                messages=messages, schema=schema, temperature=temperature
            )

            # If the caller passed a Pydantic model, validate here
            if isinstance(schema, type) and issubclass(schema, BaseModel):
                try:
                    # Validate and convert to dict
                    return schema.model_validate(raw).model_dump()
                except Exception as e:
                    logger.error(f"Error validating LLM response against schema: {str(e)}")
                    raise ValueError(f"LLM response failed schema validation: {str(e)}")

            return raw
        except Exception as e:
            logger.error(f"Error getting structured LLM response: {str(e)}")
            raise

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name})"
