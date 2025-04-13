from typing import Dict, Any, List
from pydantic import Field, BaseModel


class ToolDependency(BaseModel):
    """Model for tool dependencies."""

    tool: str
    required_by: List[str] = []
    provides: List[str] = []
    weight: int = 1  # Cost/complexity weight


class PlannerState(BaseModel):
    """State for planner agent."""

    type: str = Field(default="PlannerState")
    tool_graph: Dict[str, ToolDependency] = Field(default_factory=dict)
    cached_plans: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class PlannerConfig(BaseModel):
    """Configuration for planner agent."""

    name: str = Field(default="planner")
    system_message: str = Field(
        default="You are a planner agent responsible for creating execution strategies."
    )
    tool_cache_ttl: int = Field(default=300)  # 5 minutes
    max_plan_cache_size: int = Field(default=100)
