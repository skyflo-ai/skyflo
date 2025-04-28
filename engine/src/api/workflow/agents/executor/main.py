"""Executor agent implementation for workflow."""

from typing import (
    Dict,
    Any,
    Mapping,
    Optional,
    List,
    Callable,
    Awaitable,
)
from api.workflow.agents.executor.prompt_templates import EXECUTOR_SYSTEM_PROMPT
import logging
import json
import uuid
import asyncio
from datetime import datetime
import re

from api.workflow.agents.executor.prompt_templates import (
    SUMMARIZATION_SYSTEM_PROMPT,
    POD_SELECTION_SYSTEM_PROMPT,
    RESOURCE_RESOLUTION_SYSTEM_PROMPT,
    SUMMARIZATION_USER_PROMPT,
    RESOURCE_RESOLUTION_USER_PROMPT,
    POD_SELECTION_USER_PROMPT,
)

from api.workflow.agents.executor.types import (
    ExecutorState,
    ExecutorConfig,
)

from api.workflow.agents.base import BaseAgent
from api.services.mcp_client import MCPClient
from api.services.llm_client import LLMClient
from api.config import settings

logger = logging.getLogger(__name__)

# Add at the top level of the file, outside any class
_approval_events: Dict[str, asyncio.Event] = {}
_step_approval_status: Dict[str, bool] = {}


# Add these functions at module level
async def wait_for_approval(step_id: str, timeout: float = 300) -> bool:
    """
    Wait for user approval of a tool call.
    Returns True if approved, False if rejected or timeout.
    """
    if step_id not in _approval_events:
        _approval_events[step_id] = asyncio.Event()

    try:
        await asyncio.wait_for(_approval_events[step_id].wait(), timeout)
        return _step_approval_status.get(step_id, False)
    except asyncio.TimeoutError:
        logger.warning(f"Approval timeout for step {step_id}")
        return False
    finally:
        # Cleanup
        _approval_events.pop(step_id, None)
        _step_approval_status.pop(step_id, None)


def handle_tool_call_approval(step_id: str):
    """Handle the approval/rejection of a tool call"""
    if step_id in _approval_events:
        _step_approval_status[step_id] = True
        _approval_events[step_id].set()


def handle_tool_call_rejection(step_id: str):
    """Handle the rejection of a tool call"""
    if step_id in _approval_events:
        _approval_events[step_id].set()
        _step_approval_status[step_id] = False


class ExecutorAgent(BaseAgent):
    """Agent responsible for executing the planned operations."""

    component_type = "skyflo.agents.ExecutorAgent"
    component_config_schema = ExecutorConfig

    def __init__(
        self,
        name: str = "executor",
        system_message: str = None,
        model_context=None,
        description: Optional[str] = None,
        event_callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
    ):
        """Initialize the executor agent."""
        system_message = EXECUTOR_SYSTEM_PROMPT
        super().__init__(
            name=name,
            system_message=system_message,
            model_context=model_context,
            description=description or "Skyflo executor agent that implements plans",
        )
        self._model_context = model_context or {}  # Store model_context as instance variable
        self.mcp_client = MCPClient(event_callback=event_callback)
        self._state = ExecutorState()
        self._config = ExecutorConfig()
        self.llm_client = LLMClient(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
            temperature=settings.OPENAI_EXECUTOR_TEMPERATURE,
        )
        self.event_callback = event_callback

    async def _get_tool_info(
        self, tool_name: str, category: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get tool information from the API."""
        try:
            # Check cache first
            if tool_name in self._state.tool_info_cache:
                cached_info = self._state.tool_info_cache[tool_name]
                if (
                    datetime.now() - cached_info.get("timestamp", datetime.min)
                ).total_seconds() < self._config.tool_info_cache_ttl:
                    return cached_info["info"]

            # Fetch fresh data
            tools = await self.mcp_client.get_tools(category)
            if "tools" in tools:
                for tool in tools["tools"]:
                    if tool["name"] == tool_name:
                        tool_info = {"info": tool, "timestamp": datetime.now()}
                        self._state.tool_info_cache[tool_name] = tool_info
                        return tool

            raise ValueError(f"Tool {tool_name} not found")
        except Exception as e:
            logger.error(f"Error fetching tool info for {tool_name}: {str(e)}")
            raise

    def _estimate_token_count(self, data: Any) -> int:
        """Estimate token count from data (rough approximation: ~4 chars per token)."""
        if data is None:
            return 0

        try:
            # Convert to JSON string to count tokens
            json_str = json.dumps(data)
            # Rough approximation: ~4 chars per token
            return len(json_str) // 4
        except:
            # If serialization fails, try to use string representation
            return len(str(data)) // 4

    async def _summarize_execution_state(
        self, execution_state: Dict[str, Any], user_query: str
    ) -> Dict[str, Any]:
        """Summarize the execution state when it exceeds token limits."""
        logger.debug(f"Summarizing execution state due to token limit being exceeded")

        try:
            # Store the original execution state as a historical snapshot
            snapshot = {
                "timestamp": datetime.now().isoformat(),
                "total_steps_executed": sum(1 for k in execution_state if k.startswith("step_")),
                "token_estimate": self._estimate_token_count(execution_state),
            }
            self._state.summarization_history.append(snapshot)

            # Prepare the summarization prompt
            summarization_prompt = [
                {
                    "role": "system",
                    "content": SUMMARIZATION_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": SUMMARIZATION_USER_PROMPT.format(
                        user_query=user_query, execution_state=json.dumps(execution_state, indent=2)
                    ),
                },
            ]

            # Get summary from LLM
            summary_text = await self.llm_client.chat_completion(
                messages=summarization_prompt,
                temperature=settings.OPENAI_EXECUTOR_TEMPERATURE,
            )

            # Extract and parse JSON
            try:
                # Try to find and extract JSON from the response
                json_start = summary_text.find("{")
                json_end = summary_text.rfind("}") + 1

                if json_start >= 0 and json_end > json_start:
                    cleaned_json = summary_text[json_start:json_end]
                    summary = json.loads(cleaned_json)

                    # Add metadata about the summarization
                    summary["_meta"] = {
                        "summarized_at": datetime.now().isoformat(),
                        "steps_summarized": sum(
                            1 for k in execution_state if k.startswith("step_")
                        ),
                        "original_token_count": self._estimate_token_count(execution_state),
                        "summary_token_count": self._estimate_token_count(summary),
                    }

                    # Create new execution state with just the summary and metadata
                    new_execution_state = {
                        "_summary": summary,
                        "_summarization_occurred": True,
                    }

                    # Update token count
                    self._state.token_count = self._estimate_token_count(new_execution_state)

                    logger.debug(
                        f"Successfully summarized execution state. Original tokens: {self._state.token_count}, New tokens: {self._estimate_token_count(new_execution_state)}"
                    )
                    return new_execution_state
            except Exception as e:
                logger.error(f"Error parsing LLM summary response: {str(e)}")

            # Fallback to basic summarization if LLM method fails
            return self._fallback_summarize_execution_state(execution_state)

        except Exception as e:
            logger.error(f"Error in execution state summarization: {str(e)}")
            return self._fallback_summarize_execution_state(execution_state)

    def _fallback_summarize_execution_state(
        self, execution_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Basic fallback method to summarize execution state when LLM fails."""
        summary = {
            "_meta": {
                "summarized_at": datetime.now().isoformat(),
                "steps_summarized": sum(1 for k in execution_state if k.startswith("step_")),
                "summarization_method": "fallback",
            },
            "resources_found": {},
            "key_outputs": {},
        }

        # Extract resource information
        for key, value in execution_state.items():
            if key.startswith("step_") and isinstance(value, dict):
                # Store outputs from successful steps
                if value.get("status") == "success" and "output" in value:
                    # Try to identify resources in the output
                    if isinstance(value.get("output"), dict) and "items" in value.get("output", {}):
                        resource_type = value.get("parameters", {}).get("resource_type", "resource")
                        # Extract resource names
                        resources = []
                        for item in value.get("output", {}).get("items", []):
                            if (
                                isinstance(item, dict)
                                and "metadata" in item
                                and "name" in item.get("metadata", {})
                            ):
                                resources.append(item["metadata"]["name"])

                        if resources:
                            summary["resources_found"][resource_type] = resources

                    # Keep the most recent successful outputs (last 3)
                    if len(summary["key_outputs"]) < 3:
                        summary["key_outputs"][key] = {
                            "tool": value.get("tool"),
                            "action": value.get("action"),
                            "output_summary": (
                                str(value.get("output"))[:500] + "..."
                                if isinstance(value.get("output"), str)
                                and len(str(value.get("output"))) > 500
                                else value.get("output")
                            ),
                        }

        # Create new execution state with just the summary
        new_execution_state = {
            "_summary": summary,
            "_summarization_occurred": True,
        }

        return new_execution_state

    async def execute_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a plan's steps."""
        logger.debug(f"Starting plan execution with ID: {plan.get('plan_id')}")
        logger.debug(f"Full plan details: {json.dumps(plan, indent=2)}")

        # Store the user query in model_context for use in recursive steps
        self._model_context["user_query"] = plan.get("query", "No query available")
        logger.debug(f"User query in model_context: {self._model_context.get('user_query')}")

        try:
            if not plan.get("steps"):
                logger.warning("No steps found in plan")
                return self._create_execution_result(
                    status="skipped",
                    steps_executed=0,
                    steps_total=0,
                    results=[],
                    error="No steps to execute",
                    execution_state={},
                )

            steps = plan.get("steps", [])
            logger.debug(f"Found {len(steps)} steps to execute")

            # Normalize steps to ensure parameters are in dictionary format
            steps = self._normalize_steps(steps)

            results = []
            steps_executed = 0
            steps_total = len(steps)
            execution_state = {}
            context = {}  # Context to store dynamic values from previous steps

            # Initialize token count tracking
            self._state.token_count = 0
            self._state.summarization_history = []

            for step in steps:
                try:
                    step_id = step.get("step_id")
                    logger.debug(
                        f"\n{'='*50}\nExecuting step {step_id}: {step.get('tool')} - {step.get('action')}"
                    )
                    logger.debug(f"Step details: {json.dumps(step, indent=2)}")

                    # Check token count before executing step
                    current_token_count = self._estimate_token_count(execution_state)
                    logger.debug(
                        f"Current token count before step {step_id}: {current_token_count}"
                    )
                    self._state.token_count = current_token_count

                    # If token count exceeds limit, summarize and clear context
                    if current_token_count > self._state.max_token_limit:
                        logger.warning(
                            f"Token count ({current_token_count}) exceeds limit ({self._state.max_token_limit}). Summarizing execution state..."
                        )
                        execution_state = await self._summarize_execution_state(
                            execution_state, self._model_context.get("user_query", "")
                        )
                        logger.debug(
                            f"Execution state summarized. New token count: {self._estimate_token_count(execution_state)}"
                        )

                    # Get tool information before execution
                    tool_name = step.get("tool")
                    category = step.get("category")
                    logger.debug(f"Fetching tool info for {tool_name} (category: {category})")
                    tool_info = await self._get_tool_info(tool_name, category)
                    logger.debug(f"Tool info: {json.dumps(tool_info, indent=2)}")

                    # Check for dynamic parameters that need to be resolved
                    logger.debug(
                        f"Original parameters: {json.dumps(step.get('parameters', {}), indent=2)}"
                    )
                    parameters = await self._resolve_dynamic_parameters(
                        step.get("parameters", {}), context, execution_state
                    )
                    logger.debug(f"Resolved parameters: {json.dumps(parameters, indent=2)}")

                    # Check if this is a recursive step
                    if step.get("recursive", False):
                        logger.debug(f"Step {step_id} is marked as recursive")
                        logger.debug(
                            f"Current execution state: {json.dumps(execution_state, indent=2)}"
                        )
                        result = await self._execute_recursive_step(
                            step, parameters, tool_info, execution_state, context
                        )
                    else:
                        logger.debug(f"Validating parameters for step {step_id}")
                        # Validate parameters against tool info
                        self._validate_parameters(parameters, tool_info)

                        # Update the step with resolved parameters
                        resolved_step = step.copy()
                        resolved_step["parameters"] = parameters

                        result = await self._execute_step(resolved_step)

                    results.append(result)
                    steps_executed += 1

                    # Store the result in execution state
                    execution_state[f"step_{step.get('step_id')}"] = result
                    if result.get("output"):
                        execution_state["output"] = result.get("output")

                    # Update context with this step's results for use by future steps
                    self._update_execution_context(context, step.get("step_id"), result)

                    # Update token count after step execution
                    new_token_count = self._estimate_token_count(execution_state)
                    logger.debug(
                        f"Token count after step {step_id}: {new_token_count} (change: +{new_token_count - current_token_count})"
                    )
                    self._state.token_count = new_token_count

                    if result.get("status") == "failed":
                        logger.error(f"Step {step.get('step_id')} failed: {result.get('error')}")
                        return self._create_execution_result(
                            status="failed",
                            steps_executed=steps_executed,
                            steps_total=steps_total,
                            results=results,
                            error=f"Step {step.get('step_id')} failed: {result.get('error')}",
                            execution_state=execution_state,
                        )

                except Exception as e:
                    logger.error(f"Error executing step {step.get('step_id')}: {str(e)}")
                    return self._create_execution_result(
                        status="failed",
                        steps_executed=steps_executed,
                        steps_total=steps_total,
                        results=results,
                        error=f"Error executing step {step.get('step_id')}: {str(e)}",
                        execution_state=execution_state,
                    )

            # Final execution result
            result = self._create_execution_result(
                status="completed",
                steps_executed=steps_executed,
                steps_total=steps_total,
                results=results,
                error=None,
                execution_state=execution_state,
            )

            # Add summarization metadata if summarization occurred
            if self._state.summarization_history:
                result["summarization_history"] = self._state.summarization_history
                result["token_management"] = {
                    "final_token_count": self._state.token_count,
                    "summarizations_performed": len(self._state.summarization_history),
                    "max_token_limit": self._state.max_token_limit,
                }

            return result

        except Exception as e:
            logger.error(f"Error in plan execution: {str(e)}")
            return self._create_execution_result(
                status="failed",
                steps_executed=0,
                steps_total=0,
                results=[],
                error=str(e),
                execution_state={},
            )

    async def _execute_recursive_step(
        self,
        step: Dict[str, Any],
        parameters: Dict[str, Any],
        tool_info: Dict[str, Any],
        execution_state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a recursive step by automatically processing multiple resources."""
        logger.debug(f"Starting recursive execution for step {step.get('step_id')}")

        try:
            # First, check if we already have multiple resources identified in context
            param_resources = {}
            for param_name, param_value in parameters.items():
                # Check if we have a list of resources for this parameter
                all_resources_key = f"all_{param_name}s"
                if all_resources_key in context and isinstance(context[all_resources_key], list):
                    param_resources[param_name] = context[all_resources_key]
                    logger.debug(
                        f"Found {len(context[all_resources_key])} resources for {param_name}"
                    )

            # If no multi-resources found in context, try to generate them
            if not param_resources:
                # Generate tool calls through LLM
                tool_calls = await self._generate_recursive_tool_calls(
                    step, parameters, execution_state, context
                )

                # Execute each tool call
                sub_results = []
                for tool_call in tool_calls:
                    # Validate and execute the tool call
                    self._validate_parameters(tool_call.get("parameters", {}), tool_info)
                    result = await self._execute_step(tool_call)
                    sub_results.append(result)
            else:
                # We have resource lists in context, use them directly
                sub_results = []

                # Identify the parameter to iterate over
                iterate_param = next(iter(param_resources.keys()))
                resources = param_resources[iterate_param]

                # Create and execute a step for each resource
                for resource in resources:
                    # Create a copy of the step with the specific resource
                    resource_step = step.copy()
                    resource_params = parameters.copy()
                    resource_params[iterate_param] = resource
                    resource_step["parameters"] = resource_params

                    # Execute the step for this resource
                    logger.debug(f"Executing recursive step for {iterate_param}={resource}")
                    result = await self._execute_step(resource_step)
                    sub_results.append(result)

            # Create a composite result combining all sub-results
            composite_result = {
                "step_id": step.get("step_id"),
                "status": "success",
                "tool": step.get("tool"),
                "action": step.get("action"),
                "parameters": parameters,
                "output": "\n\n".join(
                    [
                        f"=== {r.get('parameters', {}).get('name', r.get('parameters', {}).get(iterate_param, 'Resource'))} ===\n{r.get('output', '')}"
                        for r in sub_results
                        if r.get("status") == "success"
                    ]
                ),
                "sub_results": sub_results,
                "result": {
                    "success": True,
                    "data": [
                        r.get("result", {}).get("data")
                        for r in sub_results
                        if r.get("status") == "success"
                    ],
                    "error": None,
                },
            }

            # If any sub-steps failed, report partial success
            failed_count = sum(1 for r in sub_results if r.get("status") != "success")
            if failed_count > 0:
                composite_result["result"]["partial_failure"] = True
                composite_result["result"]["success_count"] = len(sub_results) - failed_count
                composite_result["result"]["failure_count"] = failed_count

                # Include error information
                if failed_count == len(sub_results):
                    composite_result["status"] = "failed"
                    composite_result["result"]["success"] = False
                    composite_result["result"]["error"] = "All recursive operations failed"
                else:
                    composite_result["status"] = "partial_success"

            return composite_result

        except Exception as e:
            logger.error(f"Error in recursive step execution: {str(e)}", exc_info=True)
            # Fall back to original step as a safety measure
            return await self._execute_step(step)

    async def _generate_recursive_tool_calls(
        self,
        step: Dict[str, Any],
        parameters: Dict[str, Any],
        execution_state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Generate tool calls for recursive operations using LLM."""
        prompt_messages = [
            {
                "role": "system",
                "content": """You are a Kubernetes operations expert. Your task is to analyze the execution context and generate appropriate tool calls for recursive operations.

Key Objectives:
1. Analyze previous step outputs to identify items that need recursive processing
2. Generate tool calls with the same structure as the original step
3. Replace placeholder parameters with actual resource names
4. Ensure all generated calls maintain the same tool and action

For each resource discovered in previous steps, generate a separate tool call.
The tool calls should follow the exact same pattern as the original step, but with concrete parameters.""",
            },
            {
                "role": "user",
                "content": f"""
Current Step:
{json.dumps(step, indent=2)}

Current Parameters:
{json.dumps(parameters, indent=2)}

Previous Execution Context:
{json.dumps(context, indent=2)}

Execution State:
{json.dumps(execution_state, indent=2)}

User Query:
{self._model_context.get('user_query', 'No query available')}

Generate appropriate tool calls for recursively processing resources.
Return a JSON array of tool calls that follow the same structure as the current step.""",
            },
        ]

        # Get LLM response
        response_text = await self._get_llm_response(prompt_messages)

        try:
            # Extract and parse JSON
            json_start = response_text.find("[")
            json_end = response_text.rfind("]") + 1

            if json_start != -1 and json_end > 0:
                tool_calls = json.loads(response_text[json_start:json_end])
                logger.debug(f"Generated {len(tool_calls)} recursive tool calls")
                return tool_calls
        except Exception as e:
            logger.error(f"Failed to parse LLM response for recursive calls: {str(e)}")

        # Fallback: create a single tool call with original parameters
        logger.warning("Using fallback for recursive tool calls")
        return [step]

    def _validate_parameters(self, parameters: Dict[str, Any], tool_info: Dict[str, Any]) -> None:
        """Validate parameters against tool information."""
        required_params = [p for p in tool_info["parameters"] if p["required"]]
        for param in required_params:
            if param["name"] not in parameters:
                raise ValueError(f"Missing required parameter: {param['name']}")

        # Validate parameter types
        for param_name, param_value in parameters.items():
            param_info = next((p for p in tool_info["parameters"] if p["name"] == param_name), None)
            if param_info:
                expected_type = param_info["type"]
                if not self._is_valid_type(param_value, expected_type):
                    raise ValueError(
                        f"Invalid type for parameter {param_name}: expected {expected_type}"
                    )

        # Additional validation for Kubernetes resource types
        if "resource_type" in parameters and tool_info.get("name", "").startswith("kubectl"):
            self._validate_kubernetes_resource_type(parameters["resource_type"])

    def _validate_kubernetes_resource_type(self, resource_type: str) -> None:
        """Validate that a Kubernetes resource type is valid."""
        valid_resource_types = [
            "pods",
            "pod",
            "services",
            "service",
            "deployments",
            "deployment",
            "namespaces",
            "namespace",
            "ingresses",
            "ingress",
            "all",
            "crds",
            "configmaps",
            "secrets",
            "pv",
            "pvc",
            "nodes",
            "events",
        ]

        if resource_type.lower() not in valid_resource_types:
            suggested_type = "pods"  # Default suggestion
            # Try to suggest a valid resource type based on context
            if resource_type.lower() in ["po", "pod"]:
                suggested_type = "pods"
            elif resource_type.lower() in ["svc"]:
                suggested_type = "services"
            elif resource_type.lower() in ["deploy"]:
                suggested_type = "deployments"
            elif resource_type.lower() in ["ns"]:
                suggested_type = "namespaces"
            elif resource_type.lower() in ["ing"]:
                suggested_type = "ingresses"
            elif resource_type.lower() in ["cm"]:
                suggested_type = "configmaps"

            logger.warning(
                f"Invalid Kubernetes resource type: '{resource_type}'. "
                f"Using suggested type: '{suggested_type}' instead. "
                f"Valid types are: {', '.join(valid_resource_types)}"
            )

            raise ValueError(
                f"Invalid Kubernetes resource type: '{resource_type}'. "
                f"Did you mean '{suggested_type}'? "
                f"Valid types are: {', '.join(valid_resource_types)}"
            )

    def _is_valid_type(self, value: Any, expected_type: str) -> bool:
        """Check if a value matches the expected type."""
        type_mapping = {
            "<class 'str'>": str,
            "<class 'int'>": int,
            "<class 'float'>": float,
            "<class 'bool'>": bool,
            "<class 'list'>": list,
            "<class 'dict'>": dict,
        }

        if expected_type in type_mapping:
            return isinstance(value, type_mapping[expected_type])

        # Handle Optional types
        if "typing.Optional" in expected_type:
            base_type = expected_type.split("[")[1].split("]")[0]
            return value is None or self._is_valid_type(value, base_type)

        return True  # Default to True for unknown types

    async def _execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single step."""
        try:
            tool = step.get("tool")
            action = step.get("action")
            parameters = step.get("parameters", {})
            step_id = step.get("step_id", "unknown")

            if not tool or not action:
                return {
                    "step_id": step_id,
                    "status": "failed",
                    "error": "Missing tool or action",
                }

            # Log the step that's about to be executed
            logger.debug(f"Executing step {step_id}: {tool} {action}")

            # Get tool info to check if approval is required
            tool_info = await self._get_tool_info(tool, step.get("category"))
            approval_required = tool_info.get("approval_required", False)

            # Get conversation ID from context if available
            conversation_id = None
            if self._model_context and "conversation_id" in self._model_context:
                conversation_id = self._model_context.get("conversation_id")

            # Emit event that we're about to execute this step
            if hasattr(self, "event_callback") and self.event_callback:
                await self.event_callback(
                    {
                        "type": "step_about_to_execute",
                        "agent": "executor",
                        "message": f"About to execute {tool} {action}",
                        "phase": "executing",
                        "state": "execute",
                        "details": {
                            "step_id": step_id,
                            "tool": tool,
                            "action": action,
                            "parameters": parameters,
                            "status": "pending",
                            "conversation_id": conversation_id,
                            "approval_required": approval_required,
                        },
                    }
                )
                # Small delay to ensure the event is processed
                await asyncio.sleep(0.5)

            # If approval is required, emit an approval request event
            if approval_required:
                logger.debug(f"Step {step_id} requires approval")
                if hasattr(self, "event_callback") and self.event_callback:
                    await self.event_callback(
                        {
                            "type": "approval_required",
                            "agent": "executor",
                            "message": f"Approval required for {tool} {action}",
                            "phase": "executing",
                            "state": "waiting_approval",
                            "details": {
                                "step_id": step_id,
                                "tool": tool,
                                "action": action,
                                "parameters": parameters,
                                "status": "waiting_approval",
                                "conversation_id": conversation_id,
                            },
                        }
                    )
                    # Wait for approval if required
                    approved = await wait_for_approval(step_id)

                    if not approved:
                        logger.warning(f"Step {step_id} was rejected or timed out")
                        await self.event_callback(
                            {
                                "type": "step_rejected",
                                "details": {
                                    "step_id": step_id,
                                    "message": "Step was rejected by user or timed out",
                                },
                            }
                        )
                        return {
                            "step_id": step_id,
                            "status": "failed",
                            "error": "Step was rejected by user or timed out",
                        }
                    logger.debug(f"Step {step_id} was approved")
                    await asyncio.sleep(0.5)

            # Special handling for log requests which often confuse resource types and names
            if action.lower() in ["logs", "log", "get_logs"]:
                user_query = self._model_context.get("user_query", "")
                parameters = await self._preprocess_log_request(parameters, user_query)
                logger.debug(f"Preprocessed log request parameters for step {step_id}")

            # Basic validation for Kubernetes resource types
            elif "resource_type" in parameters and tool.startswith("kubectl"):
                try:
                    self._validate_kubernetes_resource_type(parameters["resource_type"])
                except ValueError as e:
                    # Attempt to correct the resource type
                    logger.debug(f"Correcting invalid resource type in step {step_id}")
                    if "pods" in str(e):
                        parameters["resource_type"] = "pods"
                    elif "services" in str(e):
                        parameters["resource_type"] = "services"
                    elif "deployments" in str(e):
                        parameters["resource_type"] = "deployments"
                    elif "namespaces" in str(e):
                        parameters["resource_type"] = "namespaces"
                    elif "ingresses" in str(e):
                        parameters["resource_type"] = "ingresses"
                    else:
                        # Default to pods for log-related actions
                        if action.lower() in ["logs", "log", "get_logs"]:
                            parameters["resource_type"] = "pods"
                            # If there was a resource type, it might be a pod name pattern
                            if "resource_type" in parameters and parameters[
                                "resource_type"
                            ] not in ["pods", "pod"]:
                                if "selector" not in parameters:
                                    parameters["selector"] = parameters["resource_type"]
                    logger.debug(f"Resource type corrected for step {step_id}")

            # Emit step execution started event
            if hasattr(self, "event_callback") and self.event_callback:
                await self.event_callback(
                    {
                        "type": "step_executing",
                        "agent": "executor",
                        "message": f"Executing {tool} {action}",
                        "phase": "executing",
                        "state": "execute",
                        "details": {
                            "step_id": step_id,
                            "tool": tool,
                            "action": action,
                            "parameters": parameters,
                            "status": "executing",
                            "conversation_id": conversation_id,
                        },
                    }
                )
                # Small delay to ensure the event is processed
                await asyncio.sleep(0.5)

            # Execute the tool with action context
            logger.debug(f"Calling tool {tool} with action {action}")

            # Get conversation ID from context if available
            conversation_id = None
            if self._model_context and "conversation_id" in self._model_context:
                conversation_id = self._model_context.get("conversation_id")

            result = await self.mcp_client.call_tool(
                tool, parameters, action=action, conversation_id=conversation_id
            )

            if tool == "wait_for_x_seconds":
                logger.debug(f"Waiting for x seconds: {parameters['seconds']} seconds")
                await asyncio.sleep(parameters["seconds"])
                logger.debug(f"Done waiting for {parameters['seconds']} seconds")

            logger.debug(f"Step {step_id} execution completed")

            # Create a properly structured execution result
            execution_result = {
                "step_id": step_id,
                "status": "success",
                "tool": tool,
                "action": action,
                "parameters": parameters,
                "output": result.get("result", {}),  # Store the actual output from result field
                "result": {
                    "success": True,
                    "data": result.get("result", {}),  # Store the result data
                    "error": None,
                },
            }

            # Emit step execution completed event
            if hasattr(self, "event_callback") and self.event_callback:
                await self.event_callback(
                    {
                        "type": "step_complete",
                        "agent": "executor",
                        "message": f"Step {step_id} completed successfully",
                        "phase": "executing",
                        "state": "execute",
                        "details": {
                            "step_id": step_id,
                            "tool": tool,
                            "action": action,
                            "parameters": parameters,
                            "status": "completed",
                            "output": result.get("result", {}),
                            "conversation_id": conversation_id,
                        },
                    }
                )
                # Small delay to ensure the event is processed
                await asyncio.sleep(0.5)

            # Update metrics
            self._update_execution_metrics(execution_result)

            return execution_result

        except Exception as e:
            step_id = step.get("step_id", "unknown")
            logger.error(f"Step {step_id} execution failed: {str(e)}")

            error_result = {
                "step_id": step_id,
                "status": "failed",
                "tool": tool,
                "action": action,
                "parameters": parameters,
                "output": str(e),  # Store error as output
                "error": str(e),
                "result": {"success": False, "data": None, "error": str(e)},
            }

            # Emit step execution failed event
            if hasattr(self, "event_callback") and self.event_callback:
                await self.event_callback(
                    {
                        "type": "step_failed",
                        "agent": "executor",
                        "message": f"Step {step_id} failed: {str(e)}",
                        "phase": "executing",
                        "state": "execute",
                        "details": {
                            "step_id": step_id,
                            "tool": tool,
                            "action": action,
                            "parameters": parameters,
                            "status": "failed",
                            "error": str(e),
                            "conversation_id": conversation_id,
                        },
                    }
                )
                # Small delay to ensure the event is processed
                await asyncio.sleep(0.5)

            # Update metrics for failed execution
            self._update_execution_metrics(error_result)

            return error_result

    def _update_execution_metrics(self, result: Dict[str, Any]) -> None:
        """Update execution metrics based on the result."""
        self._state.execution_metrics.total_executions += 1
        if result["status"] == "success":
            self._state.execution_metrics.successful_executions += 1
        else:
            self._state.execution_metrics.failed_executions += 1
        self._state.execution_metrics.last_execution_time = datetime.now()

    def _create_execution_result(self, **kwargs) -> Dict[str, Any]:
        """Create an execution result dictionary."""
        return {
            "execution_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "execution_state": kwargs.pop("execution_state", {}),
            **kwargs,
        }

    async def save_state(self) -> Mapping[str, Any]:
        """Save executor agent state."""
        base_state = await super().save_state()
        state = ExecutorState(
            inner_state=base_state.get("inner_state", {}),
            execution_metrics=self._state.execution_metrics,
            tool_metrics=self._state.tool_metrics,
            tool_info_cache=self._state.tool_info_cache,
            token_count=self._state.token_count,
            summarization_history=self._state.summarization_history,
            max_token_limit=self._state.max_token_limit,
        )
        return state.model_dump()

    async def load_state(self, state: Mapping[str, Any]) -> None:
        """Load executor agent state."""
        await super().load_state(state)
        self._state = ExecutorState(**state)

    async def _resolve_dynamic_parameters(
        self, parameters: Dict[str, Any], context: Dict[str, Any], execution_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve dynamic parameters generically for any resource type."""
        resolved_params = parameters.copy()

        try:
            # First identify if we have any placeholder parameters
            placeholder_params = {}
            for param_name, param_value in parameters.items():
                if isinstance(param_value, str) and "{EXTRACTED_FROM_STEP" in param_value:
                    placeholder_params[param_name] = param_value

            if not placeholder_params:
                return parameters  # No resolution needed

            logger.debug(f"Found placeholders to resolve: {list(placeholder_params.keys())}")

            # Get the execution state in a standard format
            steps_data = execution_state.get("execution_state", execution_state)

            # This is the generic resolution logic that works for any resource type
            resolved_resource_params = await self._resolve_resource_references(
                placeholder_params, steps_data, context, self._model_context.get("user_query", "")
            )

            # Update our parameters with any successfully resolved values
            for param_name, resolved_value in resolved_resource_params.items():
                if resolved_value is not None:  # Only update if we got a valid resolution
                    resolved_params[param_name] = resolved_value
                    logger.debug(f"Resolved parameter {param_name} to: {resolved_value}")

            return resolved_params

        except Exception as e:
            logger.error(f"Error in dynamic parameter resolution: {str(e)}", exc_info=True)
            return parameters  # Return original parameters if resolution fails

    async def _resolve_resource_references(
        self,
        placeholder_params: Dict[str, str],
        execution_state: Dict[str, Any],
        context: Dict[str, Any],
        user_query: str,
    ) -> Dict[str, Any]:
        """
        Generic resolution function for any resource reference.
        Works for any resource type (pods, ingresses, services, etc.)
        """
        resolved_values = {}

        # Build context from previous steps
        resource_context = self._build_resource_context(execution_state)
        logger.debug(f"Built resource context with {len(resource_context)} resource listings")

        # Format parameters for the LLM prompt
        placeholder_info = []
        for param_name, placeholder in placeholder_params.items():
            # Extract step number from placeholder like {EXTRACTED_FROM_STEP_1}
            step_match = re.search(r"{EXTRACTED_FROM_STEP_(\d+)}", placeholder)
            step_num = step_match.group(1) if step_match else "unknown"

            placeholder_info.append(
                {
                    "parameter_name": param_name,
                    "placeholder": placeholder,
                    "referenced_step": step_num,
                }
            )

        # Build the prompt for resolution
        prompt_messages = [
            {
                "role": "system",
                "content": RESOURCE_RESOLUTION_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": RESOURCE_RESOLUTION_USER_PROMPT.format(
                    placeholder_info=json.dumps(placeholder_info, indent=2),
                    user_query=user_query,
                    resource_context=json.dumps(resource_context, indent=2),
                    context=json.dumps(context, indent=2),
                ),
            },
        ]

        # Get response from LLM
        try:
            response_text = await self._get_llm_response(prompt_messages)

            # Extract and parse JSON
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start != -1 and json_end > 0:
                resolution_result = json.loads(response_text[json_start:json_end])
                logger.debug(f"LLM resolved resources: {resolution_result}")

                # Validate the returned values
                for param_name, resolved_value in resolution_result.items():
                    if param_name in placeholder_params:
                        # Check if the LLM still returned a placeholder
                        if (
                            isinstance(resolved_value, str)
                            and "{EXTRACTED_FROM_STEP" in resolved_value
                        ):
                            logger.warning(
                                f"LLM failed to fully resolve {param_name}: {resolved_value}"
                            )
                        else:
                            resolved_values[param_name] = resolved_value

                            # For comma-separated lists of resources, convert to array if needed
                            if isinstance(resolved_value, str) and "," in resolved_value:
                                resources = [r.strip() for r in resolved_value.split(",")]
                                # Store this separately in context for potential recursive operations
                                context[f"all_{param_name}s"] = resources
                                # For the immediate resolution, use the first item
                                resolved_values[param_name] = resources[0]
                                logger.debug(f"Split multi-resource {param_name} into: {resources}")

                return resolved_values

        except Exception as e:
            logger.error(f"Error in LLM-based resource resolution: {str(e)}", exc_info=True)

        # Fallback mechanism if LLM resolution fails
        for param_name, placeholder in placeholder_params.items():
            # Try to extract step number
            step_match = re.search(r"{EXTRACTED_FROM_STEP_(\d+)}", placeholder)
            if step_match:
                step_num = step_match.group(1)
                step_key = f"step_{step_num}"

                # Find the referenced step
                if step_key in execution_state:
                    step_data = execution_state[step_key]

                    # Try to extract resource name based on the tool used
                    if isinstance(step_data, dict):
                        resource_type = step_data.get("parameters", {}).get("resource_type", "")
                        resource_names = self._extract_resource_names_from_output(
                            step_data.get("output", ""), resource_type, param_name
                        )

                        if resource_names:
                            resolved_values[param_name] = resource_names[0]
                            if len(resource_names) > 1:
                                context[f"all_{param_name}s"] = resource_names

        return resolved_values

    def _build_resource_context(self, execution_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Build a structured context of all resource discovery steps.
        This makes it easier for the LLM to find resources.
        """
        resource_context = []

        for step_key, step_data in execution_state.items():
            if not isinstance(step_data, dict):
                continue

            # Only include steps that involve resource discovery
            if step_data.get("tool") in ["get_resources", "kubectl", "helm", "argo"]:
                resource_entry = {
                    "step_id": step_key.replace("step_", ""),
                    "tool": step_data.get("tool"),
                    "action": step_data.get("action"),
                    "parameters": step_data.get("parameters", {}),
                    "resource_type": step_data.get("parameters", {}).get(
                        "resource_type", "unknown"
                    ),
                }

                # Add output info in a structured way
                output = step_data.get("output", "")
                if output:
                    # For string outputs, add as is
                    if isinstance(output, str):
                        resource_entry["output_text"] = output
                    # For structured data, extract core fields
                    elif isinstance(output, dict):
                        resource_entry["output_structured"] = True
                        if "items" in output:
                            resource_entry["resource_count"] = len(output.get("items", []))
                            # Extract just the essential metadata
                            resource_entry["resources"] = [
                                {
                                    "name": item.get("metadata", {}).get("name", ""),
                                    "namespace": item.get("metadata", {}).get("namespace", ""),
                                    "kind": item.get("kind", ""),
                                }
                                for item in output.get("items", [])
                            ]

                resource_context.append(resource_entry)

        return resource_context

    def _extract_resource_names_from_output(
        self, output: Any, resource_type: str, param_name: str
    ) -> List[str]:
        """
        Generic extractor for any resource names from command output.
        Works with any resource type based on the output format.
        """
        resource_names = []

        if not output:
            return resource_names

        try:
            # Handle string output (typical kubectl output)
            if isinstance(output, str):
                lines = output.strip().split("\n")
                if len(lines) > 1:  # Header + at least one resource
                    for line in lines[1:]:  # Skip header
                        parts = line.split()
                        if parts:
                            resource_names.append(parts[0])  # First column is typically the name

            # Handle dict output with items array (API server response)
            elif isinstance(output, dict) and "items" in output:
                for item in output["items"]:
                    name = item.get("metadata", {}).get("name")
                    if name:
                        resource_names.append(name)
        except Exception as e:
            logger.warning(f"Error extracting resource names: {str(e)}")

        logger.debug(f"Extracted {len(resource_names)} {resource_type} names: {resource_names}")
        return resource_names

    def _update_execution_context(
        self, context: Dict[str, Any], step_id: str, result: Dict[str, Any]
    ):
        """Update the execution context with results from a step."""
        # Add basic result data to context
        context[f"step_{step_id}_status"] = result.get("status")
        context[f"step_{step_id}_output"] = result.get("output")

        # For get_resources, parse the output to add specific resource information
        if result.get("tool") == "get_resources":
            output = result.get("output")
            resource_type = result.get("parameters", {}).get("resource_type")

            if resource_type and output:
                # Store the raw output
                context[f"{resource_type}_list"] = output

                # Try to extract resource names if it's a structured response
                try:
                    # Handle both string outputs and structured data
                    if isinstance(output, str):
                        # Simple extraction of resource names from output text
                        lines = output.strip().split("\n")
                        if len(lines) > 1:  # Skip header line
                            resource_names = []
                            for line in lines[1:]:  # Skip header
                                parts = line.split()
                                if parts:
                                    resource_names.append(parts[0])
                            context[f"{resource_type}_names"] = resource_names
                    elif isinstance(output, dict) and "items" in output:
                        # Handle structured K8s API response
                        resource_names = [
                            item.get("metadata", {}).get("name") for item in output["items"]
                        ]
                        context[f"{resource_type}_names"] = resource_names
                except Exception as e:
                    logger.warning(f"Failed to extract resource names from output: {str(e)}")

    async def _extract_pod_names_from_previous_results(
        self, execution_state: Dict[str, Any], user_query: str
    ) -> List[str]:
        """Extract specific pod names from previous get_resources results that are relevant to the user query."""
        pod_names = []

        logger.debug(f"execution_state type: {type(execution_state)}")
        logger.debug(f"user_query type: {type(user_query)}")
        logger.debug(f"execution_state: {execution_state}")
        logger.debug(f"user_query: {user_query}")

        try:
            # Collect context from execution state
            context_info = []
            pod_output = ""

            for step_key, step_result in execution_state.items():
                # Add step information to context
                if step_key.startswith("step_"):
                    logger.debug(f"Building context for step: {step_key}: {step_result}")
                    context_info.append(
                        {
                            "step_id": step_key.replace("step_", ""),
                            "tool": step_result.get("tool"),
                            "action": step_result.get("action"),
                            "description": step_result.get("description", ""),
                            "parameters": step_result.get("parameters", {}),
                        }
                    )

                    # Collect pod output from get_resources steps
                    if (
                        step_result.get("tool") == "get_resources"
                        and step_result.get("parameters", {}).get("resource_type") == "pod"
                    ):
                        pod_output = step_result.get("output", "")

            logger.debug(
                f"Context info in _extract_pod_names_from_previous_results: {context_info}"
            )
            last_tool_used = context_info[-1]["tool"] if context_info else "None"
            last_namespace = context_info[-1]["parameters"].get("namespace", "default")

            logger.debug(
                f"Last tool used in _extract_pod_names_from_previous_results: {last_tool_used}"
            )
            logger.debug(
                f"Last namespace in _extract_pod_names_from_previous_results: {last_namespace}"
            )

            # Build prompt for the LLM to directly identify the relevant pod names
            prompt_messages = [
                {
                    "role": "system",
                    "content": POD_SELECTION_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": POD_SELECTION_USER_PROMPT.format(
                        user_query=user_query,
                        step_count=len(context_info),
                        last_tool=last_tool_used,
                        target_namespace=last_namespace,
                        step_details=json.dumps(context_info, indent=2),
                        pod_output=pod_output,
                    ),
                },
            ]

            logger.debug(
                f"Prompt messages in _extract_pod_names_from_previous_results: {prompt_messages}"
            )

            # Get pod names directly from LLM
            pod_names_response = await self._get_llm_response(prompt_messages)

            # The response should be a list of pod names, one per line
            if pod_names_response:
                # Split by newline and remove any empty lines
                pod_names = [
                    name.strip() for name in pod_names_response.strip().split("\n") if name.strip()
                ]
                logger.debug(f"LLM identified relevant pod names: {pod_names}")

        except Exception as e:
            logger.error(f"Failed to extract pod names using LLM: {str(e)}")
            # If LLM extraction fails, fall back to getting all pods from get_resources steps
            for step_key, step_result in execution_state.items():
                if not step_key.startswith("step_"):
                    continue

                if (
                    step_result.get("tool") == "get_resources"
                    and step_result.get("parameters", {}).get("resource_type") == "pod"
                ):
                    output = step_result.get("output")
                    if not output:
                        continue

                    namespace = step_result.get("parameters", {}).get("namespace")
                    logger.debug(f"Falling back to processing all pods from namespace: {namespace}")

                    try:
                        # Parse the output to extract pod names
                        if isinstance(output, str):
                            lines = output.strip().split("\n")
                            if len(lines) > 1:  # Skip header
                                for line in lines[1:]:
                                    parts = line.split()
                                    if parts:
                                        pod_names.append(parts[0])
                        elif isinstance(output, dict) and "items" in output:
                            # Handle structured K8s API response
                            for item in output["items"]:
                                pod_name = item.get("metadata", {}).get("name", "")
                                if pod_name:
                                    pod_names.append(pod_name)
                    except Exception as e:
                        logger.warning(f"Failed to extract pod names from output: {str(e)}")

        # Log what we found
        if pod_names:
            logger.debug(f"Extracted pod names: {pod_names}")
        else:
            logger.warning("No pods found matching the user query")

        return pod_names

    async def _preprocess_log_request(
        self, parameters: Dict[str, Any], user_query: str
    ) -> Dict[str, Any]:
        """Preprocess log request parameters to handle common issues with log requests."""
        logger.debug(f"Preprocessing log request with parameters: {parameters}")
        logger.debug(f"User query: {user_query}")

        # Make a copy to avoid modifying the original
        processed_params = parameters.copy()

        # If resource_type is not "pods" for a log request, it's likely a mistake
        if "resource_type" in processed_params and processed_params["resource_type"] != "pods":
            original_type = processed_params["resource_type"]

            # If it's a log request, the resource type should always be pods
            processed_params["resource_type"] = "pods"

            # The original resource_type might actually be a pod name pattern or label
            if "selector" not in processed_params and "name" not in processed_params:
                # Analyze the query to determine if it's likely a name pattern or label
                if "all" in user_query.lower() and original_type.lower() in user_query.lower():
                    # If "all X pods" pattern, it's likely a label selector
                    processed_params["selector"] = f"app={original_type}"
                    logger.debug(
                        f"Interpreted '{original_type}' as label selector: app={original_type}"
                    )
                else:
                    # Otherwise, assume it's a name pattern
                    processed_params["name"] = original_type
                    logger.debug(
                        f"Interpreted '{original_type}' as pod name pattern: {original_type}"
                    )

            logger.debug(
                f"Corrected resource_type from '{original_type}' to 'pods' for log request"
            )

        # Ensure namespace is set for log requests
        if "namespace" not in processed_params:
            # Check if namespace is mentioned in the query
            namespace_keywords = ["namespace", "ns"]
            for keyword in namespace_keywords:
                if keyword in user_query.lower():
                    # Try to extract namespace from the query
                    words = user_query.lower().split()
                    if keyword in words:
                        idx = words.index(keyword)
                        if idx + 1 < len(words):
                            namespace = words[idx + 1].strip(".,;:()[]{}\"'")
                            processed_params["namespace"] = namespace
                            logger.debug(f"Extracted namespace '{namespace}' from query")
                            break

            # Default to "default" namespace if not specified
            if "namespace" not in processed_params:
                processed_params["namespace"] = "default"
                logger.debug("Using default namespace for log request")

        return processed_params

    def _normalize_steps(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize steps to ensure parameters are in dictionary format.

        Converts parameters from the new list format [{"name": "key", "value": "val"}]
        to the old dictionary format {"key": "val"}.

        Args:
            steps: List of steps with parameters in either format

        Returns:
            List of steps with parameters in dictionary format
        """
        normalized_steps = []
        for step in steps:
            normalized_step = step.copy()
            if isinstance(normalized_step.get("parameters"), list):
                # Convert from [{"name": "key", "value": "val"}] to {"key": "val"}
                normalized_step["parameters"] = {
                    param.get("name"): param.get("value")
                    for param in normalized_step["parameters"]
                    if isinstance(param, dict) and "name" in param and "value" in param
                }
            normalized_steps.append(normalized_step)
        return normalized_steps
