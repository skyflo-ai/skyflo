"""Verifier agent implementation for workflow."""

import logging
import uuid
import json
from typing import Dict, Any, Mapping, Optional, List, Callable, Awaitable
from datetime import datetime

from api.workflow.agents.base import BaseAgent
from api.services.mcp_client import MCPClient
from api.workflow.agents.verifier.types import VerifierState, VerifierConfig
from api.workflow.agents.verifier.prompt_templates import (
    VERIFIER_SYSTEM_PROMPT,
    CRITERION_VALIDATION_SYSTEM_PROMPT,
    VERIFY_CRITERION_PROMPT,
    VERIFICATION_SUMMARY_PROMPT,
    VERIFY_MULTIPLE_CRITERIA_PROMPT,
)
from api.config.settings import settings
from api.llm_schemas import (
    CriterionValidation,
    VerificationSummary,
    MultiCriterionValidationList,
)

logger = logging.getLogger(__name__)


class VerifierAgent(BaseAgent):
    """Agent responsible for verifying execution results."""

    component_type = "skyflo.agents.VerifierAgent"
    component_config_schema = VerifierConfig

    def __init__(
        self,
        name: str = "verifier",
        system_message: str = None,
        model_context=None,
        description: Optional[str] = None,
        event_callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
    ):
        """Initialize the verifier agent."""
        system_message = system_message or VERIFIER_SYSTEM_PROMPT
        super().__init__(
            name=name,
            system_message=system_message,
            model_context=model_context,
            description=description or "Skyflo verifier agent that validates results",
        )
        self._model_context = model_context or {}
        self.mcp_client = MCPClient(event_callback=event_callback)
        self._state = VerifierState()
        self._config = VerifierConfig()
        self.event_callback = event_callback

    async def verify_execution(
        self,
        plan: Dict[str, Any],
        execution_state: Dict[str, Any],
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Verify the execution results of a plan."""
        logger.debug(f"Verifying execution results for plan: {plan.get('plan_id')}")

        try:
            # 1. Emit event at the start of verification process
            await self._emit_event(
                "verification_started",
                f"Starting verification process for plan: {plan.get('plan_id', 'unknown')}",
                conversation_id,
                {
                    "plan_id": plan.get("plan_id", "unknown"),
                    "conversation_id": conversation_id,
                    "timestamp": datetime.now().isoformat(),
                },
            )

            # Generate our own validation criteria instead of using plan's criteria
            validation_criteria = await self._generate_validation_criteria(plan, execution_state)
            logger.debug(f"Generated {len(validation_criteria)} validation criteria independently")

            # 2. Emit event after criteria generation
            await self._emit_event(
                "verification_criteria_list",
                f"Verifying execution with {len(validation_criteria)} criteria",
                conversation_id,
                {
                    "criteria": validation_criteria,
                    "total_criteria": len(validation_criteria),
                    "conversation_id": conversation_id,
                },
            )

            # Always use batch verification for independently generated criteria
            validation_results = await self._verify_all_criteria_llm(
                validation_criteria, execution_state
            )

            # Determine overall status
            all_success = all(r["status"] == "success" for r in validation_results)
            status = "success" if all_success else "failure"

            # Log results
            if status == "success":
                logger.debug("All validation criteria met successfully")
            else:
                failed_criteria = [
                    r["criterion"] for r in validation_results if r["status"] == "failure"
                ]
                logger.warning(f"Verification failed for criteria: {failed_criteria}")

            # Generate a verification summary if configured
            if self._config.generate_summary:
                summary = await self._generate_verification_summary(
                    validation_results, plan, execution_state
                )
                verification_result = self._create_verification_result(
                    status=status,
                    validation_results=validation_results,
                    summary=summary,
                    error=None,
                )
            else:
                verification_result = self._create_verification_result(
                    status=status,
                    validation_results=validation_results,
                    error=None,
                )

            # 3. Emit completion event with results
            await self._emit_event(
                "verification_complete",
                f"Verification {status}: {len(validation_results)} criteria checked",
                conversation_id,
                {
                    "status": status,
                    "criteria_count": len(validation_criteria),
                    "success_count": sum(1 for r in validation_results if r["status"] == "success"),
                    "failure_count": sum(1 for r in validation_results if r["status"] == "failure"),
                    "validation_results": validation_results,
                    "conversation_id": conversation_id,
                },
            )

            return verification_result

        except Exception as e:
            logger.error(f"Error in verification process: {str(e)}")
            await self._emit_event(
                "verification_error",
                f"Verification error: {str(e)}",
                conversation_id,
                {
                    "error": str(e),
                    "conversation_id": conversation_id,
                },
            )
            return self._create_verification_result(
                status="failure",
                validation_results=[],
                error=str(e),
            )

    async def _generate_validation_criteria(
        self, plan: Dict[str, Any], execution_state: Dict[str, Any]
    ) -> List[str]:
        """Generate validation criteria based on the plan and execution state."""
        logger.debug("Generating validation criteria independently")

        try:
            # Extract user query and intent from the plan
            user_query = plan.get("query", "")
            intent = plan.get("intent", "")

            # Extract step information from the plan
            steps = plan.get("steps", [])
            step_descriptions = []
            for step in steps:
                if isinstance(step, dict):
                    description = step.get("description", "")
                    tool = step.get("tool", "")
                    step_descriptions.append(f"{tool}: {description}")

            # Format the plan and execution state for the prompt
            plan_summary = {
                "query": user_query,
                "intent": intent,
                "step_count": len(steps),
                "steps": step_descriptions[:5],  # Limit to first 5 steps to save tokens
            }

            # Build prompt for the LLM
            prompt_messages = [
                {
                    "role": "system",
                    "content": """You are a verification expert for Kubernetes operations. 
Your task is to generate appropriate validation criteria for a Kubernetes operation.
Based on the user query, plan intent, and execution results, generate specific criteria that 
would verify if the operation was successful. Focus on the actual outcomes that matter to the user.

Important guidelines for generating criteria:
1. For simple read-only queries (get, list, describe), generate 1-2 core criteria focused on data retrieval success
2. For operations with side effects (create, update, delete), generate 2-3 criteria including state verification
3. For complex multi-step operations, generate 3-5 criteria covering each major step
4. Only include log verification criteria if logs are specifically part of the user's request
5. Focus on the essential outcomes that matter to the user, not implementation details""",
                },
                {
                    "role": "user",
                    "content": f"""Generate validation criteria for this operation:

USER QUERY: {user_query}

PLAN SUMMARY: {json.dumps(plan_summary, indent=2)}

Based on this information, generate appropriate validation criteria that would verify if 
the operation was successful. Each criterion should be specific, measurable, and focused on 
the outcomes that matter for the user's original request.

Note: The number of criteria should be proportional to the complexity of the operation.
- Simple read operations need only 1-2 criteria
- Operations with side effects need 2-3 criteria
- Complex multi-step operations need 3-5 criteria

Return a JSON array of validation criteria as strings.""",
                },
            ]

            # Get response from LLM
            response_text = await self._get_llm_response(
                prompt_messages, settings.OPENAI_VERIFIER_TEMPERATURE
            )
            logger.debug(f"LLM response for criteria generation: {response_text}")

            # Extract and parse JSON
            json_start = response_text.find("[")
            json_end = response_text.rfind("]") + 1

            if json_start == -1 or json_end == 0:
                logger.warning(f"Failed to extract JSON array from LLM response: {response_text}")
                # Fallback: Create basic criteria
                return [
                    f"The operation to {intent} was executed successfully",
                    f"The execution completed without critical errors",
                    f"The user's request to {user_query} was fulfilled",
                ]

            criteria = json.loads(response_text[json_start:json_end])

            # Validate the criteria format
            if not isinstance(criteria, list):
                logger.warning("Criteria not returned as a list, using fallback")
                return [
                    f"The operation to {intent} was executed successfully",
                    f"The execution completed without critical errors",
                    f"The user's request to {user_query} was fulfilled",
                ]

            # Ensure we have at least some criteria
            if not criteria:
                logger.warning("No criteria generated, using fallback")
                return [
                    f"The operation to {intent} was executed successfully",
                    f"The execution completed without critical errors",
                    f"The user's request to {user_query} was fulfilled",
                ]

            return criteria

        except Exception as e:
            logger.error(f"Error generating validation criteria: {str(e)}")
            # Return fallback criteria if generation fails
            return [
                "Operation executed without critical errors",
                "All operations completed",
                "User request was processed",
            ]

    async def _verify_all_criteria_llm(
        self, criteria: List[str], execution_state: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Verify all criteria at once using a single LLM call for efficiency."""
        logger.debug(f"Verifying {len(criteria)} criteria at once with LLM")

        # Format the criteria list for the prompt
        criteria_list = "\n".join([f"{i+1}. {criterion}" for i, criterion in enumerate(criteria)])

        # Process execution state to extract outputs and step results
        outputs = []
        step_results = {}

        # Extract outputs and step results from execution state
        if execution_state and "execution_state" in execution_state:
            steps = execution_state["execution_state"]
            for step_key, step_data in steps.items():
                if isinstance(step_data, dict):
                    if step_key.startswith("step_"):
                        step_results[step_key] = step_data
                        if "output" in step_data:
                            outputs.append(f"OUTPUT from {step_key}: {step_data['output']}")

        if "output" in execution_state:
            outputs.append(f"FINAL OUTPUT: {execution_state['output']}")

        if "error" in execution_state and execution_state["error"]:
            outputs.append(f"ERROR: {execution_state['error']}")

        outputs_text = "\n".join(outputs) if outputs else "No outputs available"

        # Format step results for better LLM understanding
        step_results_formatted = []
        for step_key, step_data in step_results.items():
            step_results_formatted.append(
                f"STEP {step_key}:\n"
                f"Tool: {step_data.get('tool', 'Unknown')}\n"
                f"Parameters: {json.dumps(step_data.get('parameters', {}), indent=2)}\n"
                f"Status: {step_data.get('status', 'Unknown')}"
            )

        step_results_text = (
            "\n".join(step_results_formatted)
            if step_results_formatted
            else "No step results available"
        )

        # Update the prompt to explicitly state we want an object with a validations array
        prompt_messages = [
            {"role": "system", "content": CRITERION_VALIDATION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": VERIFY_MULTIPLE_CRITERIA_PROMPT.format(
                    criteria_list=criteria_list,
                    outputs=outputs_text,
                    step_results=step_results_text,
                ),
            },
        ]

        # Get structured response using the wrapper class instead of List type
        validation_result = await self._get_structured_llm_response(
            prompt_messages, MultiCriterionValidationList, settings.OPENAI_VERIFIER_TEMPERATURE
        )
        logger.debug(f"LLM structured batch verification response: {validation_result}")

        # Extract the validations list from the response
        if hasattr(validation_result, "model_dump"):
            result_dict = validation_result.model_dump()
            criteria_results = result_dict.get("validations", [])
        else:
            criteria_results = validation_result.get("validations", [])

        # Convert to the standard format used by the verification process
        validation_results = []
        for result in criteria_results:
            # If it's a nested dict, extract properties directly
            if isinstance(result, dict):
                validation_results.append(
                    {
                        "criterion": result.get("criterion", "Unknown criterion"),
                        "status": ("success" if result.get("criterion_met", False) else "failure"),
                        "details": result.get("reasoning", "No reasoning provided"),
                        "confidence": result.get("confidence", 0.5),
                    }
                )
            # If it's a Pydantic model or has model_dump method
            elif hasattr(result, "model_dump"):
                result_dict = result.model_dump()
                validation_results.append(
                    {
                        "criterion": result_dict.get("criterion", "Unknown criterion"),
                        "status": (
                            "success" if result_dict.get("criterion_met", False) else "failure"
                        ),
                        "details": result_dict.get("reasoning", "No reasoning provided"),
                        "confidence": result_dict.get("confidence", 0.5),
                    }
                )

        return validation_results

    async def _validate_criterion_llm(
        self, criterion: str, execution_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate a criterion using LLM."""
        logger.debug(f"Validating criterion with LLM: {criterion}")

        # Process execution state
        outputs = []
        step_results = {}

        # Extract outputs and step results from execution state
        if execution_state and "execution_state" in execution_state:
            steps = execution_state["execution_state"]
            for step_key, step_data in steps.items():
                if isinstance(step_data, dict):
                    if step_key.startswith("step_"):
                        step_results[step_key] = step_data
                        if "output" in step_data:
                            outputs.append(f"OUTPUT from {step_key}: {step_data['output']}")

        if "output" in execution_state:
            outputs.append(f"FINAL OUTPUT: {execution_state['output']}")

        if "error" in execution_state and execution_state["error"]:
            outputs.append(f"ERROR: {execution_state['error']}")

        outputs_text = "\n".join(outputs) if outputs else "No outputs available"

        # Format step results for better LLM understanding
        step_results_formatted = []
        for step_key, step_data in step_results.items():
            step_results_formatted.append(
                f"STEP {step_key}:\n"
                f"Tool: {step_data.get('tool', 'Unknown')}\n"
                f"Parameters: {json.dumps(step_data.get('parameters', {}), indent=2)}\n"
                f"Status: {step_data.get('status', 'Unknown')}"
            )

        step_results_text = (
            "\n".join(step_results_formatted)
            if step_results_formatted
            else "No step results available"
        )

        # Build prompt for LLM using the template from prompt_templates.py
        prompt_messages = [
            {"role": "system", "content": CRITERION_VALIDATION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": VERIFY_CRITERION_PROMPT.format(
                    criterion=criterion, outputs=outputs_text, step_results=step_results_text
                ),
            },
        ]

        # Get structured response using CriterionValidation schema
        validation_result = await self._get_structured_llm_response(
            prompt_messages, CriterionValidation, settings.OPENAI_VERIFIER_TEMPERATURE
        )
        logger.debug(f"LLM structured criterion validation response: {validation_result}")

        # Convert to dict if it's a Pydantic model
        if hasattr(validation_result, "model_dump"):
            result = validation_result.model_dump()
        else:
            result = validation_result

        # Ensure all required fields are present
        if "criterion_met" not in result:
            result["criterion_met"] = False
        if "confidence" not in result:
            result["confidence"] = 0.5
        if "reasoning" not in result:
            result["reasoning"] = "No reasoning provided by LLM"

        return result

    async def _generate_verification_summary(
        self,
        validation_results: List[Dict[str, Any]],
        plan: Dict[str, Any],
        execution_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate a summary of the verification results."""
        logger.debug("Generating verification summary")

        try:
            # Format validation results for the prompt
            criteria_results = json.dumps(validation_results, indent=2)

            # Get user query from plan
            user_query = plan.get("query", "No query available")

            # Format plan for the prompt (simplified to reduce token usage)
            simplified_plan = {
                "intent": plan.get("intent", "No intent specified"),
                "step_count": len(plan.get("steps", [])),
            }
            original_plan = json.dumps(simplified_plan, indent=2)

            # Build prompt for LLM
            prompt_messages = [
                {"role": "system", "content": VERIFIER_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": VERIFICATION_SUMMARY_PROMPT.format(
                        criteria_results=criteria_results,
                        user_query=user_query,
                        original_plan=original_plan,
                    ),
                },
            ]

            # Get structured response using VerificationSummary schema
            summary_result = await self._get_structured_llm_response(
                prompt_messages, VerificationSummary, settings.OPENAI_VERIFIER_TEMPERATURE
            )
            logger.debug(f"LLM structured verification summary response: {summary_result}")

            # Convert to dict if it's a Pydantic model
            if hasattr(summary_result, "model_dump"):
                summary = summary_result.model_dump()
            else:
                summary = summary_result

            return summary

        except Exception as e:
            logger.error(f"Error generating verification summary: {str(e)}")
            return {
                "overall_success": all(r["status"] == "success" for r in validation_results),
                "summary": f"Error generating detailed summary: {str(e)}",
            }

    def _create_verification_result(self, **kwargs) -> Dict[str, Any]:
        """Create a standardized verification result."""
        return {
            "verification_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            **kwargs,
        }

    async def _emit_event(
        self,
        event_type: str,
        message: str,
        conversation_id: Optional[str],
        details: Dict[str, Any],
    ) -> None:
        """Emit an event if callback is available."""
        if hasattr(self, "event_callback") and self.event_callback:
            await self.event_callback(
                {
                    "type": event_type,
                    "agent": "verifier",
                    "message": message,
                    "phase": "verifying",
                    "state": "verify",
                    "conversation_id": conversation_id,
                    "details": details,
                    "data": {"conversation_id": conversation_id},
                }
            )

    async def save_state(self) -> Mapping[str, Any]:
        """Save verifier agent state."""
        base_state = await super().save_state()
        state = VerifierState(
            inner_state=base_state.get("inner_state", {}),
            verification_metrics=self._state.verification_metrics,
            validation_history=self._state.validation_history,
        )
        return state.model_dump()

    async def load_state(self, state: Mapping[str, Any]) -> None:
        """Load verifier agent state."""
        await super().load_state(state)
        self._state = VerifierState(**state)
