"""Type definitions for executor agent."""

from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import Field, BaseModel

from ..base import BaseAgentState, BaseAgentConfig


class ExecutionMetrics(BaseModel):
    """Metrics for tool execution."""

    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    total_retries: int = 0
    average_execution_time: float = 0.0
    last_execution_time: Optional[datetime] = None


class ToolMetrics(BaseModel):
    """Metrics for individual tools."""

    success_rate: float = 0.0
    average_latency: float = 0.0
    error_frequency: Dict[str, int] = Field(default_factory=dict)
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None


class ExecutorState(BaseAgentState):
    """State for executor agent."""

    type: str = Field(default="ExecutorState")
    execution_metrics: ExecutionMetrics = Field(default_factory=ExecutionMetrics)
    tool_metrics: Dict[str, ToolMetrics] = Field(default_factory=dict)
    tool_info_cache: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    token_count: int = Field(default=0)
    summarization_history: List[Dict[str, Any]] = Field(default_factory=list)
    max_token_limit: int = Field(default=20000)


class ExecutorConfig(BaseAgentConfig):
    """Configuration for executor agent."""

    name: str = Field(default="executor")
    system_message: str = Field(
        default="You are an executor agent responsible for implementing planned operations."
    )
    max_retries: int = Field(default=3)
    retry_delay: int = Field(default=1)
    timeout: int = Field(default=300)  # 5 minutes
    tool_info_cache_ttl: int = Field(default=300)  # 5 minutes
    max_token_limit: int = Field(default=20000)  # Maximum token limit before summarization
