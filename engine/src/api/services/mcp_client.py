"""MCP client for communication with the Engine component."""

import logging
from typing import Any, Dict, Optional, List, Type, Callable, Awaitable
import aiohttp
import asyncio
import time
from pydantic import BaseModel, create_model
from ..config import settings


logger = logging.getLogger(__name__)

# Global callback registry
_GLOBAL_CALLBACK_REGISTRY: List[Callable[[Dict[str, Any]], Awaitable[None]]] = []


def register_global_callback(callback: Callable[[Dict[str, Any]], Awaitable[None]]) -> None:
    """Register a global callback for all MCPClient instances.

    Args:
        callback: The callback function to register
    """
    if callback not in _GLOBAL_CALLBACK_REGISTRY:
        _GLOBAL_CALLBACK_REGISTRY.append(callback)
        logger.debug(
            f"Registered global callback, total callbacks: {len(_GLOBAL_CALLBACK_REGISTRY)}"
        )


async def call_all_callbacks(event: Dict[str, Any]) -> None:
    """Call all registered callbacks with the given event.

    Args:
        event: The event to pass to callbacks
    """
    logger.debug(
        f"Calling all registered callbacks ({len(_GLOBAL_CALLBACK_REGISTRY)}) for event type: {event.get('type')}"
    )
    for callback in _GLOBAL_CALLBACK_REGISTRY:
        try:
            await callback(event)
        except Exception as e:
            logger.error(f"Error in global callback: {str(e)}")


class ToolParameter(BaseModel):
    """Model for tool parameter definition."""

    name: str
    type: str
    description: Optional[str] = None
    required: bool = False
    default: Optional[Any] = None
    aliases: List[str] = []
    allow_null: bool = False


class ToolDefinition(BaseModel):
    """Model for tool definition."""

    name: str
    description: str
    category: str
    parameters: List[ToolParameter]
    return_type: str


class MCPClient:
    """Client for interacting with the MCP server."""

    def __init__(
        self, event_callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None
    ):
        """Initialize the MCP client.

        Args:
            event_callback: Optional callback function for emitting events
        """
        self.base_url = settings.MCP_SERVER_URL
        self.session = None
        self.tool_cache = {}
        self.cache_expiry = 300  # 5 minutes
        self.last_cache_update = {}
        self.tool_schemas: Dict[str, Type[BaseModel]] = {}
        self.tool_definitions: Dict[str, ToolDefinition] = {}
        self.event_callback = event_callback

        # Register this callback globally if it's not None
        if event_callback is not None:
            register_global_callback(event_callback)
            logger.debug(f"Registered event_callback in MCPClient constructor")
        else:
            logger.debug(f"MCPClient initialized with None callback")

        # Add detailed debug information for tracking instances
        import traceback

        stack = traceback.extract_stack()
        caller = stack[-2]  # Get the caller of this constructor
        logger.debug(
            f"MCPClient initialized with callback: {event_callback is not None} from {caller.filename}:{caller.lineno}"
        )
        if event_callback is None:
            logger.warning(
                f"MCPClient initialized with None callback. Stack trace: {traceback.format_stack()[-5:-1]}"
            )

    async def _ensure_session(self):
        """Ensure aiohttp session exists."""
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def close(self):
        """Close the client session."""
        if self.session:
            await self.session.close()
            self.session = None

    def _create_parameter_schema(self, tool_def: ToolDefinition) -> Type[BaseModel]:
        """Create a Pydantic model for tool parameters."""
        field_definitions = {}
        type_mapping = {
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "List[str]": List[str],
            "List[int]": List[int],
            "Dict[str, Any]": Dict[str, Any],
            "Dict[str, str]": Dict[str, str],
            "Optional[str]": Optional[str],
            "Optional[int]": Optional[int],
            "Optional[float]": Optional[float],
            "Optional[bool]": Optional[bool],
            "Optional[list]": Optional[list],
            "Optional[dict]": Optional[dict],
            "Any": Any,
        }

        for param in tool_def.parameters:
            # Safely convert type string to actual type
            param_type = type_mapping.get(param.type, Any)  # Default to Any if type not found

            if param.required:
                field_definitions[param.name] = (param_type, ...)
            else:
                field_definitions[param.name] = (param_type, param.default)

        return create_model(f"{tool_def.name}Parameters", **field_definitions)

    async def get_tools(self, category: Optional[str] = None) -> Dict[str, Any]:
        """Get available tools, optionally filtered by category.

        Args:
            category: Optional tool category (kubernetes, helm, argo)

        Returns:
            Dict containing tool definitions
        """
        cache_key = f"tools_{category or 'all'}"
        current_time = time.time()

        # Check cache validity
        if (
            cache_key in self.tool_cache
            and current_time - self.last_cache_update.get(cache_key, 0) < self.cache_expiry
        ):
            logger.debug(f"Returning cached tools for key: {cache_key}")
            return self.tool_cache[cache_key]

        # Fetch fresh data
        await self._ensure_session()
        endpoint = f"/mcp/v1/tools/{category}" if category else "/mcp/v1/tools"
        logger.debug(f"Fetching tools from endpoint: {self.base_url}{endpoint}")

        try:
            async with self.session.get(f"{self.base_url}{endpoint}") as response:
                response.raise_for_status()
                tools_data = await response.json()
                logger.debug(f"Raw tools response: {tools_data}")

                if not isinstance(tools_data, dict):
                    logger.error(
                        f"Invalid tools response format. Expected dict, got {type(tools_data)}"
                    )
                    return {"tools": []}

                if "tools" not in tools_data:
                    logger.error("No 'tools' key in response")
                    return {"tools": []}

                if not isinstance(tools_data["tools"], list):
                    logger.error(
                        f"Invalid tools list format. Expected list, got {type(tools_data['tools'])}"
                    )
                    return {"tools": []}

                # Update tool definitions and schemas
                if "tools" in tools_data:
                    for tool_data in tools_data["tools"]:
                        try:
                            tool_def = ToolDefinition(**tool_data)
                            logger.debug(f"Parsed tool definition for {tool_def.name}")
                            self.tool_definitions[tool_def.name] = tool_def
                            self.tool_schemas[tool_def.name] = self._create_parameter_schema(
                                tool_def
                            )
                        except Exception as e:
                            logger.error(f"Error parsing tool definition: {str(e)}")
                            continue

                # Update cache
                self.tool_cache[cache_key] = tools_data
                self.last_cache_update[cache_key] = current_time

                logger.debug(f"Successfully fetched {len(tools_data['tools'])} tools")
                return tools_data

        except aiohttp.ClientError as e:
            logger.error(f"HTTP error fetching tools: {str(e)}")
            return {"tools": []}
        except Exception as e:
            logger.error(f"Error fetching tools from MCP server: {str(e)}")
            return {"tools": []}

    async def get_alternative_tools(self, tool_name: str) -> List[Dict]:
        """Get alternative tools that can perform similar operations.

        Args:
            tool_name: Name of the tool to find alternatives for

        Returns:
            List of alternative tool definitions
        """
        all_tools = await self.get_tools()
        tool_info = next((t for t in all_tools if t["name"] == tool_name), None)

        if not tool_info:
            return []

        # Find tools with similar capabilities
        return [
            t
            for t in all_tools
            if t["name"] != tool_name
            and any(cap in t.get("capabilities", []) for cap in tool_info.get("capabilities", []))
        ]

    async def call_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        action: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Call a tool on the MCP server using dedicated endpoints.

        Args:
            tool_name: Name of the tool to call
            parameters: Tool parameters
            action: The action to perform, which can help derive parameters
            conversation_id: Optional ID of the conversation for event tracking

        Returns:
            Tool execution result
        """
        await self._ensure_session()

        try:
            # Ensure tool definitions are loaded
            if not self.tool_definitions:
                await self.get_tools()

            tool_def = self.tool_definitions.get(tool_name)
            if not tool_def:
                raise ValueError(f"Tool '{tool_name}' not found in available tools")

            logger.debug(f"Tool definition for {tool_name}: {tool_def}")

            # First apply action-based parameter inference
            inferred_parameters = parameters.copy()
            if action:
                # Handle common actions for get_resources
                if tool_name == "get_resources":
                    if "resource_type" not in inferred_parameters:
                        if action == "get_pods":
                            inferred_parameters["resource_type"] = "pod"
                        elif action == "get_deployments":
                            inferred_parameters["resource_type"] = "deployment"
                        elif action == "get_services":
                            inferred_parameters["resource_type"] = "service"
                        elif action == "get_namespaces":
                            inferred_parameters["resource_type"] = "namespace"
                        elif action == "get_nodes":
                            inferred_parameters["resource_type"] = "node"

            # Map parameters using aliases and handle required parameters
            mapped_parameters = {}
            missing_required = []

            for param in tool_def.parameters:
                param_value = None

                # Check direct parameter name
                if param.name in inferred_parameters:
                    param_value = inferred_parameters[param.name]
                else:
                    # Check aliases
                    for alias in param.aliases:
                        if alias in inferred_parameters:
                            param_value = inferred_parameters[alias]
                            break

                # Handle required parameters
                if param.required:
                    if param_value is None and not param.allow_null:
                        if param.default is not None:
                            param_value = param.default
                        else:
                            missing_required.append(param.name)

                if param_value is not None or param.required:
                    mapped_parameters[param.name] = param_value

            # Check for missing required parameters
            if missing_required:
                raise ValueError(
                    f"Missing required parameters for {tool_name}: {', '.join(missing_required)}"
                )

            # Validate parameters using schema
            if tool_name in self.tool_schemas:
                schema = self.tool_schemas[tool_name]
                try:
                    validated_params = schema(**mapped_parameters)
                    mapped_parameters = validated_params.model_dump()
                except Exception as e:
                    raise ValueError(
                        f"Parameter validation failed for {tool_name}: {str(e)}\n"
                        f"Parameters provided: {mapped_parameters}\n"
                        f"Required parameters: {[p.name for p in tool_def.parameters if p.required]}"
                    )

            # Use dedicated endpoint for tool execution
            endpoint = f"/mcp/v1/tools/{tool_def.category}/{tool_name}/execute"

            # Emit the tool_call_initiated event via WebSocket
            tool_call_event = {
                "type": "tool_call_initiated",
                "conversation_id": conversation_id,
                "data": {
                    "tool": tool_name,
                    "action": action,
                    "category": tool_def.category,
                    "parameters": mapped_parameters,
                    "timestamp": time.time(),
                },
            }

            # First try the instance's callback
            if self.event_callback:
                logger.debug(
                    f"Emitting tool_call_initiated event via instance callback: {tool_call_event}"
                )
                await self.event_callback(tool_call_event)

            # Also use global callbacks
            logger.debug(f"Emitting tool_call_initiated event via global callbacks")
            await call_all_callbacks(tool_call_event)

            # Small delay to ensure the event is processed
            await asyncio.sleep(0.01)

            logger.debug(
                f"Calling tool {tool_name} with parameters: {mapped_parameters}\n"
                f"Original parameters: {parameters}\n"
                f"Action: {action}"
            )

            async with self.session.post(
                f"{self.base_url}{endpoint}",
                json=mapped_parameters,
            ) as response:
                response.raise_for_status()
                result = await response.json()

                # Emit the tool_call_completed event via WebSocket
                tool_call_event = {
                    "type": "tool_call_completed",
                    "conversation_id": conversation_id,
                    "data": {
                        "tool": tool_name,
                        "action": action,
                        "category": tool_def.category,
                        "parameters": mapped_parameters,
                        "result": result,
                        "timestamp": time.time(),
                    },
                }

                # First try the instance's callback
                if self.event_callback:
                    logger.debug(
                        f"Emitting tool_call_completed event via instance callback: {tool_call_event}"
                    )
                    await self.event_callback(tool_call_event)

                # Also use global callbacks
                logger.debug(f"Emitting tool_call_completed event via global callbacks")
                await call_all_callbacks(tool_call_event)

                # Small delay to ensure the event is processed
                await asyncio.sleep(0.01)

                return result

        except ValueError as e:
            logger.error(f"Validation error for tool {tool_name}: {str(e)}")

            # Emit error event
            tool_call_event = {
                "type": "tool_call_error",
                "conversation_id": conversation_id,
                "data": {
                    "tool": tool_name,
                    "action": action,
                    "category": tool_def.category if tool_def else None,
                    "parameters": (
                        mapped_parameters if "mapped_parameters" in locals() else parameters
                    ),
                    "error": str(e),
                    "timestamp": time.time(),
                },
            }

            # First try the instance's callback
            if self.event_callback:
                logger.debug(
                    f"Emitting tool_call_error event via instance callback: {tool_call_event}"
                )
                await self.event_callback(tool_call_event)

            # Also use global callbacks
            logger.debug(f"Emitting tool_call_error event via global callbacks")
            await call_all_callbacks(tool_call_event)

            raise
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {str(e)}")

            # Emit error event
            tool_call_event = {
                "type": "tool_call_error",
                "conversation_id": conversation_id,
                "data": {
                    "tool": tool_name,
                    "action": action,
                    "category": tool_def.category if tool_def else None,
                    "parameters": (
                        mapped_parameters if "mapped_parameters" in locals() else parameters
                    ),
                    "error": str(e),
                    "timestamp": time.time(),
                },
            }

            # First try the instance's callback
            if self.event_callback:
                logger.debug(
                    f"Emitting tool_call_error event via instance callback: {tool_call_event}"
                )
                await self.event_callback(tool_call_event)

            # Also use global callbacks
            logger.debug(f"Emitting tool_call_error event via global callbacks")
            await call_all_callbacks(tool_call_event)

            raise

    async def validate_tool_access(self, tool_name: str) -> bool:
        """Validate if the tool is accessible and authorized.

        Args:
            tool_name: Name of the tool to validate

        Returns:
            True if tool is accessible and authorized
        """
        try:
            if not self.tool_definitions:
                await self.get_tools()
            return tool_name in self.tool_definitions
        except Exception as e:
            logger.error(f"Error validating tool access: {str(e)}")
            return False

    def clear_cache(self, category: Optional[str] = None):
        """Clear the tool cache.

        Args:
            category: Optional category to clear, if None clears all
        """
        if category:
            cache_key = f"tools_{category}"
            self.tool_cache.pop(cache_key, None)
            self.last_cache_update.pop(cache_key, None)
        else:
            self.tool_cache.clear()
            self.last_cache_update.clear()
            self.tool_schemas.clear()
            self.tool_definitions.clear()

    async def process_query(
        self, query: str, conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process a natural language query through the Engine workflow.

        Args:
            query: The natural language query to process
            conversation_id: Optional ID of the conversation for event tracking

        Returns:
            Dict containing the workflow result
        """
        return await self.call_tool(
            "process_query", {"query": query}, conversation_id=conversation_id
        )
