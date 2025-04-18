"""Common models for tool responses and configurations."""

from typing import Dict, Any, Optional, List, Type
from pydantic import BaseModel, Field, create_model
from datetime import datetime


class ToolResponse(BaseModel):
    """Base model for tool responses."""

    tool: str = Field(..., description="Name of the tool used")
    command: str = Field(..., description="Command that was executed")
    status: str = Field(..., description="Status of the execution (success/error)")
    result: Optional[Any] = Field(None, description="Result of the command execution")
    error: Optional[str] = Field(None, description="Error message if execution failed")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Execution timestamp"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class ParameterSchema(BaseModel):
    """Schema for tool parameters."""

    name: str = Field(..., description="Parameter name")
    type: str = Field(
        ..., description="Parameter type (string, integer, boolean, etc.)"
    )
    description: str = Field(..., description="Parameter description")
    required: bool = Field(
        default=True, description="Whether the parameter is required"
    )
    default: Optional[Any] = Field(None, description="Default value if not provided")
    validation_rules: Dict[str, Any] = Field(
        default_factory=dict, description="Validation rules for the parameter"
    )
    aliases: List[str] = Field(
        default_factory=list, description="Alternative names for the parameter"
    )


class ToolConfig(BaseModel):
    """Base model for tool configuration."""

    name: str = Field(..., description="Name of the tool")
    description: str = Field(..., description="Description of the tool")
    commands: List[str] = Field(..., description="List of available commands")
    permissions: List[str] = Field(default=["read"], description="Required permissions")
    parameters: List[ParameterSchema] = Field(
        default_factory=list, description="Tool parameter schemas"
    )
    context: Dict[str, Any] = Field(
        default_factory=dict, description="Additional context"
    )

    def get_parameter_schema(self) -> Type[BaseModel]:
        """Get a Pydantic model for parameter validation."""
        fields = {}
        for param in self.parameters:
            field_type = self._get_field_type(param.type)
            field = Field(
                ... if param.required else Optional[field_type],
                description=param.description,
                default=param.default,
            )
            fields[param.name] = (field_type, field)

            # Add aliases as additional fields
            for alias in param.aliases:
                fields[alias] = (field_type, field)

        return create_model(f"{self.name}Parameters", **fields)

    def _get_field_type(self, type_str: str) -> Type:
        """Convert string type to Python type."""
        type_map = {
            "string": str,
            "integer": int,
            "boolean": bool,
            "float": float,
            "list": List,
            "dict": Dict,
            "any": Any,
        }
        return type_map.get(type_str, Any)


class ResourceIdentifier(BaseModel):
    """Model for identifying Kubernetes resources."""

    name: str = Field(..., description="Name of the resource")
    namespace: Optional[str] = Field(None, description="Namespace of the resource")
    kind: str = Field(..., description="Kind of resource (pod, deployment, etc.)")
    api_version: str = Field(default="v1", description="API version of the resource")
