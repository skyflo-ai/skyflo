"""Pydantic models and types for planner agent."""

from typing import Dict, Any, Optional
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
