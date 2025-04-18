"""Type definitions for verifier agent."""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import Field, BaseModel

from ..base import BaseAgentState, BaseAgentConfig


class ValidationResult(BaseModel):
    """Model for validation results."""

    matches_intent: bool
    issues: List[str] = []
    confidence: float
    reasoning: str
    recommendations: List[str] = []
    metrics: Dict[str, Any] = {}


class VerificationMetrics(BaseModel):
    """Metrics for verification process."""

    total_verifications: int = 0
    successful_verifications: int = 0
    failed_verifications: int = 0
    average_confidence: float = 0.0
    common_issues: Dict[str, int] = Field(default_factory=dict)
    last_verification_time: Optional[datetime] = None


class VerifierState(BaseAgentState):
    """State for verifier agent."""

    type: str = Field(default="VerifierState")
    verification_metrics: VerificationMetrics = Field(default_factory=VerificationMetrics)
    validation_history: List[ValidationResult] = Field(default_factory=list)


class VerifierConfig(BaseAgentConfig):
    """Configuration for verifier agent."""

    name: str = Field(default="verifier")
    system_message: str = Field(
        default="You are a verifier agent responsible for validating execution results."
    )
    max_retries: int = Field(default=3)
    retry_delay: int = Field(default=1)
    timeout: int = Field(default=300)  # 5 minutes

    # New configuration options
    batch_verification: bool = Field(
        default=True,
        description="Whether to verify multiple criteria in a single LLM call when possible",
    )
    generate_summary: bool = Field(
        default=True, description="Whether to generate a summary of all verification results"
    )
    summary_confidence_threshold: float = Field(
        default=0.7, description="Confidence threshold for accepting summary results"
    )
    use_detailed_context: bool = Field(
        default=True,
        description="Whether to include detailed execution context in verification prompts",
    )
