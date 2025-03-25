"""Tool registry for Skyflo.ai MCP Server."""

from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Type, get_type_hints
from pydantic import BaseModel, Field
import asyncio
import inspect
from typing_extensions import Annotated

from .permissions import requires_approval


class ToolCategory(str, Enum):
    """Available tool categories."""

    KUBERNETES = "kubernetes"
    HELM = "helm"
    ARGO = "argo"


class ParameterInfo(BaseModel):
    """Information about a tool parameter."""

    name: str
    type: str
    description: Optional[str] = None
    required: bool = True
    default: Optional[Any] = None
    aliases: List[str] = Field(default_factory=list)
    allow_null: bool = False


class Tool(BaseModel):
    """Tool information model."""

    name: str
    description: str
    category: ToolCategory
    handler: Optional[Callable] = Field(None, exclude=True)
    config: Optional[Any] = Field(None, exclude=True)
    parameter_schema: Optional[Type[BaseModel]] = Field(None, exclude=True)
    parameters: List[ParameterInfo] = Field(default_factory=list)
    return_type: Optional[str] = None
    approval_required: bool = Field(
        default=False,
        description="Whether this tool requires approval before execution",
    )

    @classmethod
    def from_function(
        cls, func: Callable, name: str, description: str, category: ToolCategory
    ) -> "Tool":
        """Create a Tool instance from a function."""
        # Get function signature
        sig = inspect.signature(func)

        # Get type hints
        type_hints = get_type_hints(func)

        # Check if tool requires approval based on permissions
        approval_required = requires_approval(name, category.value)

        # Extract parameters
        parameters = []
        for param_name, param in sig.parameters.items():
            param_type = type_hints.get(param_name, Any)
            param_type_str = str(param_type)
            param_desc = None
            aliases = []
            allow_null = False

            # Check if the type is Optional
            if hasattr(param_type, "__origin__") and param_type.__origin__ is Optional:
                allow_null = True
                param_type_str = str(param_type.__args__[0])

            # Handle Annotated types
            if hasattr(param_type, "__origin__") and param_type.__origin__ is Annotated:
                param_type_str = str(param_type.__args__[0])
                param_desc = (
                    param_type.__args__[1] if len(param_type.__args__) > 1 else None
                )

                # Extract aliases from the description if it exists
                if param_desc and isinstance(param_desc, str):
                    # Look for alias indicators in the description
                    if "alias:" in param_desc.lower():
                        for part in param_desc.split(","):
                            if "alias:" in part.lower():
                                alias_part = part.split(":", 1)[1].strip()
                                aliases.extend(
                                    [
                                        a.strip()
                                        for a in alias_part.split("/")
                                        if a.strip()
                                    ]
                                )

            # Common aliases based on naming conventions
            if param_name == "ns":
                aliases.append("namespace")
            elif param_name == "name":
                aliases.append("resource_name")

            # Check again for Optional in the extracted type string
            if "typing.Optional" in param_type_str:
                allow_null = True

            parameters.append(
                ParameterInfo(
                    name=param_name,
                    type=param_type_str,
                    description=param_desc,
                    required=param.default is inspect.Parameter.empty,
                    default=(
                        param.default
                        if param.default is not inspect.Parameter.empty
                        else None
                    ),
                    aliases=aliases,
                    allow_null=allow_null,
                )
            )

        # Get return type
        return_type = str(type_hints.get("return", Any))

        return cls(
            name=name,
            description=description,
            category=category,
            handler=func,
            parameters=parameters,
            return_type=return_type,
            approval_required=approval_required,
        )

    def derive_parameters(
        self, action: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Derive parameters based on the action.

        Args:
            action: The action name (e.g., "get_pods")
            parameters: The original parameters

        Returns:
            Updated parameters with inferred values
        """
        # Make a copy of the parameters
        updated_params = dict(parameters)

        # Check if we have explicit mappings for this action
        if action in self.action_parameter_mappings:
            for param_name, param_value in self.action_parameter_mappings[
                action
            ].items():
                if param_name not in updated_params:
                    updated_params[param_name] = param_value

        # Handle common naming patterns
        if self.name == "get_resources" and action.startswith("get_"):
            # Extract resource type from action name
            resource_type = action[4:]  # Remove "get_" prefix
            # Handle plurals by removing trailing 's' if present
            if resource_type.endswith("s"):
                resource_type = resource_type[:-1]
            # Special cases
            if resource_type == "podslogss":  # from get_pods_logs
                resource_type = "pod"

            if "resource_type" not in updated_params:
                updated_params["resource_type"] = resource_type

        return updated_params


class ToolExecutionError(Exception):
    """Error raised when tool execution fails."""

    pass


class ToolRegistry:
    """Registry for tracking registered tools."""

    _instance = None
    _tools: Dict[str, Tool] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register_tool(
        self,
        name: str,
        description: str,
        category: ToolCategory,
        handler: Optional[Callable] = None,
        config: Optional[Any] = None,
    ):
        """Register a tool with the registry.

        Args:
            name: Tool name
            description: Tool description
            category: Tool category
            handler: Optional function to handle tool execution
            config: Optional tool configuration
        """
        parameter_schema = None
        if config and hasattr(config, "get_parameter_schema"):
            parameter_schema = config.get_parameter_schema()

        if handler:
            tool = Tool.from_function(handler, name, description, category)
            tool.config = config
            tool.parameter_schema = parameter_schema
        else:
            tool = Tool(
                name=name,
                description=description,
                category=category,
                handler=handler,
                config=config,
                parameter_schema=parameter_schema,
            )

        self._tools[name] = tool

    def get_all_tools(self) -> List[Tool]:
        """Get all registered tools."""
        return list(self._tools.values())

    def get_tools_by_category(self, category: ToolCategory) -> List[Tool]:
        """Get tools for a specific category."""
        return [tool for tool in self._tools.values() if tool.category == category]

    def get_categories(self) -> List[ToolCategory]:
        """Get all available categories that have registered tools."""
        return list(set(tool.category for tool in self._tools.values()))

    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a specific tool by name."""
        return self._tools.get(name)

    async def execute_tool(
        self, tool_name: str, parameters: Dict[str, Any], action: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a tool with the given parameters.

        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters
            action: Optional action context to help derive parameters

        Returns:
            Tool execution result

        Raises:
            ToolExecutionError: If tool execution fails
        """
        tool = self.get_tool(tool_name)
        if not tool:
            raise ToolExecutionError(f"Tool not found: {tool_name}")

        if not tool.handler:
            raise ToolExecutionError(f"No handler registered for tool: {tool_name}")

        try:
            # Derive parameters from action if provided
            if action:
                parameters = tool.derive_parameters(action, parameters)

            # Validate parameters against schema if available
            if tool.parameter_schema:
                validated_params = tool.parameter_schema(**parameters)
                parameters = validated_params.model_dump()

            if asyncio.iscoroutinefunction(tool.handler):
                result = await tool.handler(**parameters)
            else:
                result = tool.handler(**parameters)
            return {"status": "success", "result": result}
        except Exception as e:
            raise ToolExecutionError(f"Tool execution failed: {str(e)}")

    def clear(self):
        """Clear all registered tools."""
        self._tools.clear()


# Global instance
registry = ToolRegistry()
