"""Pydantic schemas for structured LLM responses."""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


# Define the new structure for parameters
class ParameterItem(BaseModel):
    """Represents a single parameter with a fixed name and value."""

    name: str = Field(description="The name of the parameter")
    value: Any = Field(description="The value of the parameter")

    model_config = ConfigDict(extra="forbid")


# Schemas for Planner's Discovery Phase
class DiscoveryStep(BaseModel):
    """Schema for a single discovery step as defined in DISCOVERY_QUERY_PROMPT."""

    step_id: str
    tool: str
    action: str
    parameters: List[ParameterItem] = Field(description="List of parameters for the tool action")
    description: str
    discovery_step: bool

    model_config = ConfigDict(extra="forbid")


class DiscoveryContext(BaseModel):
    """Schema for the discovery context as defined in DISCOVERY_QUERY_PROMPT."""

    target_resources: List[str]
    target_namespace: str
    related_resources: List[str]
    state_requirements: List[str]

    model_config = ConfigDict(extra="forbid")


class DiscoveryPlan(BaseModel):
    """Schema for the discovery plan response as defined in DISCOVERY_QUERY_PROMPT."""

    query: str
    discovery_intent: str
    steps: List[DiscoveryStep]
    discovery_context: DiscoveryContext

    model_config = ConfigDict(extra="forbid")


# Schemas for Planner's Execution Phase
class ExecutionStep(BaseModel):
    """Schema for a single execution step as defined in ANALYZE_QUERY_PROMPT."""

    step_id: str
    tool: str
    action: str
    parameters: List[ParameterItem] = Field(description="List of parameters for the tool action")
    description: str
    required: bool
    recursive: bool
    discovery_step: bool

    model_config = ConfigDict(extra="forbid")


class DiscoveryContextItem(BaseModel):
    """Schema for discovery context within execution plan as defined in ANALYZE_QUERY_PROMPT."""

    resource_type: str
    filters: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class ExecutionContext(BaseModel):
    """Schema for the execution context as defined in ANALYZE_QUERY_PROMPT."""

    requires_verification: bool
    additional_context: Optional[str] = None
    target_namespace: Optional[str] = None
    resource_type: Optional[str] = None
    discovery_context: Optional[DiscoveryContextItem] = None

    model_config = ConfigDict(extra="forbid")


class ExecutionPlan(BaseModel):
    """Schema for the execution plan response as defined in ANALYZE_QUERY_PROMPT."""

    query: str
    intent: str
    steps: List[ExecutionStep]
    context: ExecutionContext

    model_config = ConfigDict(extra="forbid")


# Schemas for Verifier Agent
class CriterionValidation(BaseModel):
    """Schema for a single criterion validation result as defined in VERIFY_CRITERION_PROMPT."""

    criterion_met: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str

    model_config = ConfigDict(extra="forbid")


class MultiCriterionValidation(BaseModel):
    """Schema for the item in the list for multiple criteria validation results as defined in VERIFY_MULTIPLE_CRITERIA_PROMPT."""

    criterion: str
    criterion_met: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str

    model_config = ConfigDict(extra="forbid")


class MultiCriterionValidationList(BaseModel):
    """Wrapper for a list of MultiCriterionValidation objects to satisfy OpenAI's requirement for object schemas."""

    validations: List[MultiCriterionValidation] = Field(
        description="List of validation results for multiple criteria"
    )

    model_config = ConfigDict(extra="forbid")


class ConfidenceMetrics(BaseModel):
    """Schema for verification confidence metrics as defined in VERIFICATION_SUMMARY_PROMPT."""

    high_confidence_validations: int
    low_confidence_validations: int
    average_confidence: float = Field(ge=0.0, le=1.0)

    model_config = ConfigDict(extra="forbid")


class VerificationSummary(BaseModel):
    """Schema for the verification summary as defined in VERIFICATION_SUMMARY_PROMPT."""

    overall_success: bool
    summary: str
    key_findings: List[str]
    recommendations: List[str]
    confidence_metrics: ConfidenceMetrics

    model_config = ConfigDict(extra="forbid")
