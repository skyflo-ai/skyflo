"""Pydantic models and types for planner agent."""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class ToolDependency:
    """Represents a tool and its dependencies."""

    def __init__(self, tool, provides=None, weight=1):
        """Initialize a tool dependency.

        Args:
            tool: The tool identifier
            provides: The capabilities this tool provides
            weight: The complexity weight of this tool
        """
        self.tool = tool
        self.provides = provides or []
        self.weight = weight
        self.required_by = []


class ExecutionMetrics(BaseModel):
    """Execution metrics for planner."""

    total_plans: int = 0
    successful_plans: int = 0
    failed_plans: int = 0
    last_plan_time: Optional[datetime] = None


class PlannerState(BaseModel):
    """State for planner agent."""

    inner_state: Dict[str, Any] = Field(default_factory=dict)
    execution_metrics: ExecutionMetrics = Field(default_factory=ExecutionMetrics)
    tool_graph: Dict[str, Any] = Field(default_factory=dict)
    cached_plans: Dict[str, Any] = Field(default_factory=dict)


class PlannerConfig(BaseModel):
    """Configuration for planner agent."""

    llm_temperature: float = 0.6
    max_plan_cache_size: int = 100
    min_wait_after_write: int = 5
    max_wait_after_write: int = 30
    verify_resources_exist: bool = True


# Schemas for structured output
class ParameterItem(BaseModel):
    """Represents a single parameter with a fixed name and value."""

    name: str = Field(description="The name of the parameter")
    value: Any = Field(description="The value of the parameter")


# Schemas for Planner's Discovery Phase
class DiscoveryStep(BaseModel):
    """Schema for a single discovery step as defined in DISCOVERY_QUERY_PROMPT."""

    step_id: str
    tool: str
    action: str
    parameters: List[ParameterItem] = Field(
        default_factory=list, description="List of parameters for the tool action"
    )
    description: str
    discovery_step: bool


class DiscoveryContext(BaseModel):
    """Schema for the discovery context as defined in DISCOVERY_QUERY_PROMPT."""

    target_resources: List[str]
    target_namespace: str
    related_resources: List[str]
    state_requirements: List[str]


class DiscoveryPlan(BaseModel):
    """Schema for the discovery plan response as defined in DISCOVERY_QUERY_PROMPT."""

    query: str
    discovery_intent: str
    steps: List[DiscoveryStep]
    discovery_context: DiscoveryContext


# Schemas for Planner's Execution Phase
class ExecutionStep(BaseModel):
    """Schema for a single execution step as defined in ANALYZE_QUERY_PROMPT."""

    step_id: str
    tool: str
    action: str
    parameters: List[ParameterItem] = Field(
        default_factory=list, description="List of parameters for the tool action"
    )
    description: str
    required: bool = True
    recursive: bool = False
    discovery_step: bool = False


class DiscoveryContextItem(BaseModel):
    """Schema for discovery context within execution plan as defined in ANALYZE_QUERY_PROMPT."""

    resource_type: str
    filters: Optional[str] = None


class ExecutionContext(BaseModel):
    """Schema for the execution context as defined in ANALYZE_QUERY_PROMPT."""

    requires_verification: bool
    additional_context: Optional[str] = None
    target_namespace: Optional[str] = None
    resource_type: Optional[str] = None
    discovery_context: Optional[DiscoveryContextItem] = None


class ExecutionPlan(BaseModel):
    """Schema for the execution plan response as defined in ANALYZE_QUERY_PROMPT."""

    query: str
    intent: str
    steps: List[ExecutionStep]
    context: ExecutionContext
