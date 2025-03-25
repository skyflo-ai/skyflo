"""Workflow manager for orchestrating agent workflows."""

import logging
import asyncio
import time
import uuid
import json
from typing import Any, Dict, List, Optional, Callable, Awaitable
from datetime import datetime

from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field
from autogen_core import CancellationToken

from ..config import settings
from ..services.mcp_client import MCPClient
from ..services.llm_client import LLMClient
from ..domain.models import Conversation, Message, User
from .agents.planner import PlannerAgent
from .agents.executor import ExecutorAgent
from .agents.verifier import VerifierAgent

logger = logging.getLogger(__name__)


class WorkflowState(BaseModel):
    """State schema for the workflow."""

    query: str
    workflow_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    start_time: float = Field(default_factory=time.time)
    discovery_state: Dict[str, Any] = {}  # Added for discovery phase
    discovery_plan: Dict[str, Any] = {}  # Added for discovery phase
    plan: Dict[str, Any] = {}
    execution_state: Dict[str, Any] = {}
    verification_result: Dict[str, Any] = {}
    response: str = ""  # Added field to store the generated response
    end_time: float = 0.0
    duration: float = 0.0
    status: str = ""
    error: str = ""
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)


class WorkflowManager:
    """Manager for orchestrating agent workflows using LangGraph."""

    def __init__(
        self, event_callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None
    ):
        """Initialize the workflow manager.

        Args:
            event_callback: Optional callback for real-time event updates
        """
        self.event_callback = event_callback
        self.planner = PlannerAgent(event_callback=event_callback)
        self.executor = ExecutorAgent(event_callback=event_callback)
        self.verifier = VerifierAgent(event_callback=event_callback)
        self.llm_client = LLMClient(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
            temperature=settings.OPENAI_TEMPERATURE,
        )
        self.graph = self._build_graph()
        self.compiled_graph = self.graph.compile()  # Compile the graph
        self.current_state = None  # Track the current workflow state
        logger.info("Workflow manager initialized with multi-agent execution graph")

    async def _emit_event(self, event_data: Dict[str, Any]) -> None:
        """Emit an event if a callback is registered.

        Args:
            event_data: Event data to emit
        """
        logger.debug(f"Attempting to emit event: {event_data.get('type')}")
        if self.event_callback:
            logger.info(f"Emitting event: {event_data.get('type')} using registered callback")
            try:
                await self.event_callback(event_data)
                logger.debug(f"Successfully emitted event: {event_data.get('type')}")
            except Exception as e:
                logger.error(
                    f"Error emitting event {event_data.get('type')}: {str(e)}", exc_info=True
                )
                # Continue execution even if event emission fails
        else:
            logger.warning(
                f"Cannot emit event {event_data.get('type')}: No event_callback registered"
            )

    def _build_graph(self) -> StateGraph:
        """Build the workflow graph using LangGraph."""
        # Create the graph with the state schema
        workflow = StateGraph(state_schema=WorkflowState)

        # Add nodes for each agent
        workflow.add_node("discovery_node", self._discovery_step)  # New discovery node
        workflow.add_node(
            "discovery_execution_node", self._execute_discovery
        )  # New discovery execution node
        workflow.add_node("planner_node", self._plan_step)
        workflow.add_node("executor_node", self._execute_step)
        workflow.add_node("verifier_node", self._verify_step)
        workflow.add_node("response_generator_node", self._generate_final_response)

        # Define edges and conditions
        workflow.add_edge(
            "discovery_node", "discovery_execution_node"
        )  # Discovery to discovery execution
        workflow.add_edge(
            "discovery_execution_node", "planner_node"
        )  # Discovery execution to planner
        workflow.add_edge("planner_node", "executor_node")
        workflow.add_conditional_edges(
            "executor_node",
            self._check_execution,
            {"success": "verifier_node", "failure": END},
        )
        workflow.add_edge("verifier_node", "response_generator_node")
        workflow.add_edge("response_generator_node", END)

        # Set the entry point to discovery node
        workflow.set_entry_point("discovery_node")

        return workflow

    async def _discovery_step(self, state: WorkflowState) -> Dict[str, Any]:
        """Execute the discovery phase to gather cluster information.

        Args:
            state: Current workflow state

        Returns:
            Updated workflow state with discovery plan
        """
        try:
            query = state.query
            logger.info(f"Starting discovery phase for query: {query[:100]}...")

            # Generate the discovery plan
            discovery_plan = await self.planner.create_discovery_plan(query, state.conversation_id)

            # Log the generated discovery plan
            logger.info(
                f"Discovery planning complete with {len(discovery_plan.get('steps', []))} steps"
            )

            # Return a dictionary with only the field to update
            return {"discovery_plan": discovery_plan}
        except Exception as e:
            logger.error(f"Error in discovery step: {str(e)}", exc_info=True)
            # Return empty discovery plan to indicate failure
            return {"discovery_plan": {"status": "error", "error": str(e), "steps": []}}

    async def _execute_discovery(self, state: WorkflowState) -> Dict[str, Any]:
        """Execute the discovery plan to gather cluster information.

        Args:
            state: Current workflow state

        Returns:
            Updated workflow state with discovery results
        """
        try:
            discovery_plan = state.discovery_plan
            logger.info(
                f"Starting discovery execution for plan: {discovery_plan.get('plan_id', 'unknown')}"
            )
            logger.info(f"Discovery plan contains {len(discovery_plan.get('steps', []))} steps")

            # Update executor's model context with conversation_id
            if state.conversation_id:
                if not self.executor._model_context:
                    self.executor._model_context = {}
                self.executor._model_context["conversation_id"] = state.conversation_id
                logger.info(
                    f"Updated executor model context with conversation_id: {state.conversation_id}"
                )

            # Execute the discovery plan
            discovery_state = await self.executor.execute_plan(discovery_plan)

            # Log the execution result
            status = discovery_state.get("status", "unknown")
            steps_executed = discovery_state.get("steps_executed", 0)
            steps_total = discovery_state.get("steps_total", 0)
            logger.info(
                f"Discovery execution complete. Status: {status}, "
                f"Steps executed: {steps_executed}/{steps_total}"
            )

            # Return a dictionary with only the field to update
            return {"discovery_state": discovery_state}
        except Exception as e:
            logger.error(f"Error in discovery execution: {str(e)}", exc_info=True)
            # Return error discovery state
            return {"discovery_state": {"status": "failed", "error": str(e)}}

    async def _plan_step(self, state: WorkflowState) -> Dict[str, Any]:
        """Execute the planning step.

        Args:
            state: Current workflow state

        Returns:
            Updated workflow state
        """
        try:
            query = state.query
            logger.info(f"Starting planning phase for query: {query[:100]}...")

            # Get discovery context from state
            discovery_context = {
                "discovery_state": state.discovery_state,
                "discovery_plan": state.discovery_plan,
            }

            # Generate the plan with discovery context
            plan = await self.planner.analyze_query(
                query, state.conversation_id, discovery_context=discovery_context
            )

            # Log the generated plan
            logger.info(f"Planning complete with {len(plan.get('steps', []))} execution steps")

            # Return a dictionary with only the field to update
            return {"plan": plan}
        except Exception as e:
            logger.error(f"Error in planning step: {str(e)}", exc_info=True)
            # Return empty plan to indicate failure
            return {"plan": {"status": "error", "error": str(e), "steps": []}}

    async def _execute_step(self, state: WorkflowState) -> Dict[str, Any]:
        """Execute the execution step."""
        try:
            plan = state.plan
            logger.info(f"Starting execution phase for plan: {plan.get('plan_id', 'unknown')}")
            logger.info(f"Plan contains {len(plan.get('steps', []))} steps to execute")

            # Update executor's model context with conversation_id
            if state.conversation_id:
                if not self.executor._model_context:
                    self.executor._model_context = {}
                self.executor._model_context["conversation_id"] = state.conversation_id
                logger.info(
                    f"Updated executor model context with conversation_id: {state.conversation_id}"
                )

            # Execute the plan
            execution_state = await self.executor.execute_plan(plan)

            # Log the execution result
            status = execution_state.get("status", "unknown")
            steps_executed = execution_state.get("steps_executed", 0)
            steps_total = execution_state.get("steps_total", 0)
            logger.info(
                f"Execution complete. Status: {status}, "
                f"Steps executed: {steps_executed}/{steps_total}"
            )

            # Return a dictionary with only the field to update
            return {"execution_state": execution_state}
        except Exception as e:
            logger.error(f"Error in execution step: {str(e)}", exc_info=True)

            # Return error execution state
            return {"execution_state": {"status": "failed", "error": str(e)}}

    def _generate_results_summary(self, execution_state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of execution results for events."""
        summary = {
            "steps_executed": execution_state.get("steps_executed", 0),
            "steps_total": execution_state.get("steps_total", 0),
            "success_count": 0,
            "failed_count": 0,
            "tools_used": set(),
        }

        # Extract success/failure counts and tools used
        if "execution_state" in execution_state:
            for step_key, step_data in execution_state["execution_state"].items():
                if isinstance(step_data, dict):
                    # Count successes and failures
                    if step_data.get("status") == "success":
                        summary["success_count"] += 1
                    elif step_data.get("status") == "failed":
                        summary["failed_count"] += 1

                    # Collect unique tools used
                    if "tool" in step_data:
                        summary["tools_used"].add(step_data["tool"])

        # Convert set to list for JSON serialization
        summary["tools_used"] = list(summary["tools_used"])

        return summary

    async def _verify_step(self, state: WorkflowState) -> Dict[str, Any]:
        """Execute the verification step."""
        try:
            plan = state.plan
            execution_state = state.execution_state
            logger.info(
                f"Starting verification phase for plan: {plan.get('plan_id', 'unknown')}, "
                f"execution: {execution_state.get('execution_id', 'unknown')}"
            )

            # Add a small delay to show progress
            await asyncio.sleep(0.5)

            # Verify the execution - pass original query to make the verifier completely independent
            verification_result = await self.verifier.verify_execution(
                plan, execution_state, state.conversation_id
            )

            # Log the verification result
            status = verification_result.get("status", "unknown")
            logger.info(f"Verification complete. Status: {status}")

            # Return a dictionary with only the field to update
            return {"verification_result": verification_result}
        except Exception as e:
            logger.error(f"Error in verification step: {str(e)}", exc_info=True)

            # Return error verification result
            return {"verification_result": {"status": "failure", "error": str(e)}}

    async def _generate_final_response(self, state: WorkflowState) -> Dict[str, Any]:
        """Generate the final response based on workflow execution.

        Args:
            state: Current workflow state with execution results

        Returns:
            Updated workflow state with response field
        """
        try:
            logger.info("Generating final response from workflow results")

            # Build context for the LLM
            user_query = state.query

            # Create the full execution context
            full_execution_context = {
                "plan": state.plan,
                "execution_results": state.execution_state,
                "verification": state.verification_result,
                "workflow_id": state.workflow_id,
            }

            # Use intelligent summarization to create a query-focused context summary
            logger.info("Beginning intelligent context summarization based on user query...")

            # Perform LLM-based intelligent summarization
            execution_context = await self.llm_client.summarize_execution_context(
                user_query=user_query,
                execution_context=full_execution_context,
                max_tokens=20000,  # Target max tokens for context
                event_callback=self.event_callback,  # Pass the event callback
                conversation_id=state.conversation_id,  # Pass the conversation ID
            )

            # Calculate context size for logging
            context_size = len(json.dumps(execution_context))
            logger.info(
                f"Prepared intelligently summarized context of size {context_size} characters"
            )

            # Emit event that we're starting response generation
            await self._emit_event(
                {
                    "type": "response_generating",
                    "agent": "response_generator",
                    "message": "Generating final response based on execution results",
                    "phase": "responding",
                    "state": "generate",
                    "conversation_id": state.conversation_id,
                    "details": {
                        "query": user_query[:100] + "..." if len(user_query) > 100 else user_query,
                        "context_size": context_size,
                        "timestamp": datetime.now().isoformat(),
                        "conversation_id": state.conversation_id,
                    },
                    "data": {
                        "progress": 0.95,
                        "message": "Generating final detailed response",
                        "conversation_id": state.conversation_id,
                    },
                }
            )

            # Build the prompt for the LLM
            prompt_messages = [
                {
                    "role": "system",
                    "content": """You are an AI assistant specialized in explaining Kubernetes operations. 
Your task is to generate a clear, concise markdown response that explains what was done in response to the user's query.

Follow these guidelines:
1. Use a conversational, helpful tone
2. Format your response with Markdown for readability
3. Explain what actions were taken and their results
4. Include relevant details from the execution context
5. For code or command outputs, use proper markdown code blocks
6. Organize information with headings and lists as appropriate
7. Focus on being informative and concise
8. Do not mention the internal workflow or the fact that you're generating this response

Your response should be formatted and ready for the user to read.""",
                },
                {
                    "role": "user",
                    "content": f"""Here's the user query: {user_query}

Here's the execution context with summarized information relevant to this query: {json.dumps(execution_context, indent=2)}

Generate formatted markdown:""",
                },
            ]

            # Get response from LLM
            response_text = await self.llm_client.chat_completion(
                messages=prompt_messages,
                temperature=0.7,  # Slightly higher temperature for more natural responses
            )

            logger.info(f"Generated response of {len(response_text)} characters")

            # Emit event that response generation is complete
            await self._emit_event(
                {
                    "type": "response_complete",
                    "agent": "response_generator",
                    "message": "Final response generation completed",
                    "phase": "responding",
                    "state": "complete",
                    "conversation_id": state.conversation_id,
                    "details": {
                        "response_length": len(response_text),
                        "timestamp": datetime.now().isoformat(),
                        "conversation_id": state.conversation_id,
                        "output": response_text,
                    },
                    "data": {
                        "progress": 1.0,
                        "message": "Response ready",
                        "conversation_id": state.conversation_id,
                        "last_step": True,
                    },
                }
            )

            # Return the generated response
            return {"response": response_text}
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}", exc_info=True)

            # Emit event for response generation failure
            await self._emit_event(
                {
                    "type": "response_error",
                    "agent": "response_generator",
                    "message": f"Error generating final response: {str(e)}",
                    "phase": "responding",
                    "state": "error",
                    "conversation_id": (
                        state.conversation_id if hasattr(state, "conversation_id") else None
                    ),
                    "details": {
                        "error": str(e),
                        "timestamp": datetime.now().isoformat(),
                        "conversation_id": (
                            state.conversation_id if hasattr(state, "conversation_id") else None
                        ),
                    },
                    "data": {
                        "progress": 0.95,
                        "message": "Error during response generation, using fallback",
                        "conversation_id": (
                            state.conversation_id if hasattr(state, "conversation_id") else None
                        ),
                    },
                }
            )

            # Return a fallback response in case of error
            return {
                "response": f"I executed your request for '{state.query}'. "
                f"The operation completed with status: {state.verification_result.get('status', 'unknown')}."
            }

    def _check_execution(self, state: WorkflowState) -> str:
        """Check execution status and determine next step."""
        execution_state = state.execution_state  # Access directly as an attribute

        # Log the execution check
        status = "unknown"
        # Handle both dictionary and object with status attribute
        if isinstance(execution_state, dict):
            status = execution_state.get("status")
            logger.info(f"Checking execution status: {status}")
            if status == "completed":
                return "success"
            else:
                logger.warning(f"Execution failed with status: {status}")
                # Emit execution failure event

                return "failure"
        else:
            status = getattr(execution_state, "status", None)
            logger.info(f"Checking execution status (object): {status}")
            if status == "completed":
                return "success"
            else:
                logger.warning(f"Execution failed with status: {status}")

                return "failure"

    def _check_verification(self, state: WorkflowState) -> str:
        """Check verification status and determine next step."""
        verification_result = state.verification_result  # Access directly as an attribute

        # Get verification status
        if isinstance(verification_result, dict):
            status = verification_result.get("status")
        else:
            status = getattr(verification_result, "status", None)

        # Log the verification check
        logger.info(f"Checking verification status: {status}")

        # Always return verified to continue to response generation regardless of status
        if status == "success":
            logger.info("Verification successful, proceeding to response generation")
            return "verified"
        else:
            logger.info("Verification didn't succeed, but proceeding to response generation anyway")
            return "failed"  # This will now go to response_generator_node

    def _detect_infinite_loop(self, state: WorkflowState) -> bool:
        """
        Detect potential infinite loops in the workflow by analyzing execution patterns.
        Returns True if a loop is detected, False otherwise.
        """
        # Only check for loops after at least one retry
        if state.retry_count < 1:
            return False

        try:
            # Check execution state for repeated failing patterns with same parameters
            execution_state = state.execution_state

            if not execution_state or "execution_state" not in execution_state:
                return False

            # Look for steps that failed with the same error repeatedly
            steps = execution_state.get("execution_state", {})
            error_patterns = []

            for step_key, step_data in steps.items():
                if not isinstance(step_data, dict):
                    continue

                if step_data.get("status") == "failed":
                    # Look for placeholder parameters that weren't properly resolved
                    for param_name, param_value in step_data.get("parameters", {}).items():
                        if isinstance(param_value, str) and "{EXTRACTED_FROM_STEP" in param_value:
                            logger.warning(
                                f"Found unresolved placeholder in {step_key}: {param_value}"
                            )
                            error_patterns.append(f"unresolved_param:{param_name}:{param_value}")

                    # Look for "not found" errors which often indicate resolution issues
                    error = step_data.get("error", "")
                    output = step_data.get("output", "")
                    if isinstance(error, str) or isinstance(output, str):
                        error_text = error if error else output
                        if "not found" in error_text or "doesn't exist" in error_text:
                            logger.warning(f"Found 'not found' error in {step_key}")
                            error_patterns.append(f"not_found:{step_key}")

            # If we found potential loop patterns, check if they're repeated across retries
            if error_patterns and hasattr(self, "_previous_error_patterns"):
                # If we see the same error patterns repeating, it's likely a loop
                if set(error_patterns) == set(self._previous_error_patterns):
                    logger.warning(
                        f"Same error patterns detected across retries, likely infinite loop"
                    )
                    return True

            # Store current patterns for future comparison
            self._previous_error_patterns = error_patterns

            return False
        except Exception as e:
            logger.error(f"Error in loop detection: {str(e)}")
            return False

    async def execute_workflow(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        event_callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
    ) -> Dict[str, Any]:
        """Execute the complete workflow for a query.

        Args:
            query: The user's natural language query
            conversation_id: Optional conversation ID for context
            user_id: Optional user ID for personalization
            event_callback: Optional callback for real-time event updates

        Returns:
            Dict containing workflow results
        """
        # Store the event callback if provided
        if event_callback:
            # Set event callback for the manager and all agents immediately
            self.event_callback = event_callback
            self.planner.event_callback = event_callback
            self.executor.event_callback = event_callback
            self.verifier.event_callback = event_callback
            # Reinitialize MCPClient with the event callback
            self.executor.mcp_client = MCPClient(event_callback=event_callback)
            logger.info("Event callback set for all agents")

        # Generate a workflow ID for tracking
        workflow_id = str(uuid.uuid4())

        # If no conversation_id is provided, generate one
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
            logger.info(f"Generated new conversation_id: {conversation_id}")

        # Initialize workflow state or update existing state
        if self.current_state is None:
            # First query, create initial state using the Pydantic model
            self.current_state = WorkflowState(
                query=query,
                workflow_id=workflow_id,
                start_time=time.time(),
                conversation_id=conversation_id,  # Always set conversation_id
                user_id=user_id,
            )
        else:
            # Update existing state with new query
            self.current_state.query = query
            self.current_state.start_time = time.time()
            self.current_state.workflow_id = workflow_id
            # Reset fields that should be recomputed
            self.current_state.end_time = 0.0
            self.current_state.duration = 0.0
            self.current_state.status = ""
            self.current_state.error = ""
            # Update context fields if provided
            self.current_state.conversation_id = conversation_id  # Always update conversation_id
            if user_id:
                self.current_state.user_id = user_id

        # Update model context for all agents
        if conversation_id:
            # Update planner's model context
            if not self.planner._model_context:
                self.planner._model_context = {}
            self.planner._model_context["conversation_id"] = conversation_id

            # Update executor's model context
            if not self.executor._model_context:
                self.executor._model_context = {}
            self.executor._model_context["conversation_id"] = conversation_id

            # Update verifier's model context
            if not self.verifier._model_context:
                self.verifier._model_context = {}
            self.verifier._model_context["conversation_id"] = conversation_id

            logger.info(
                f"Updated all agents' model contexts with conversation_id: {conversation_id}"
            )

        # Create a response state for immediate return
        immediate_response = {
            "workflow_id": workflow_id,
            "query": query,
            "status": "processing",
            "start_time": time.time(),
            "conversation_id": conversation_id,  # Include conversation_id in response
        }

        # Start workflow execution in the background without awaiting it
        # Create a new task with the current state and event callback
        state_copy = self.current_state.copy()
        # Ensure event callback is preserved for the background task
        asyncio.create_task(self._execute_workflow_async(state_copy, event_callback=event_callback))

        # Return immediate response while workflow executes in background
        return immediate_response

    async def _execute_workflow_async(
        self,
        state: WorkflowState,
        event_callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
    ) -> None:
        """Execute workflow asynchronously in background.

        Args:
            state: The workflow state to use
            event_callback: Optional callback for real-time event updates
        """
        try:
            # Ensure event callback is set for this background task
            if event_callback:
                # Set event callback for the manager and all agents
                self.event_callback = event_callback
                self.planner.event_callback = event_callback
                self.executor.event_callback = event_callback
                self.verifier.event_callback = event_callback
                # Reinitialize MCPClient with the event callback
                self.executor.mcp_client = MCPClient(event_callback=event_callback)
                logger.info("Event callbacks set for background task execution")

            # Execute the workflow
            logger.info(f"Executing workflow with state: {state}")

            try:
                # Set timeout for workflow execution
                final_state = await asyncio.wait_for(
                    self.compiled_graph.ainvoke(state),
                    timeout=settings.WORKFLOW_EXECUTION_TIMEOUT,
                )

                logger.info(f"Workflow final state: {final_state}")

                # Add completion time
                if isinstance(final_state, dict):
                    # Convert dict result to WorkflowState if needed
                    if not isinstance(final_state, WorkflowState):
                        if isinstance(state, WorkflowState):
                            # Update current state with values from final_state
                            for key, value in final_state.items():
                                setattr(state, key, value)
                            final_state = state
                        else:
                            final_state = WorkflowState(**final_state)

                # Update final state
                final_state.end_time = time.time()
                final_state.duration = final_state.end_time - final_state.start_time
                final_state.status = "completed"

                # Update current state
                self.current_state = final_state

                # Store the final assistant message in the database
                await self._store_assistant_message(final_state)

            except asyncio.TimeoutError:
                logger.error(
                    f"Workflow execution timed out after {settings.WORKFLOW_EXECUTION_TIMEOUT} seconds"
                )

                state.status = "timeout"
                state.error = f"Workflow execution timed out after {settings.WORKFLOW_EXECUTION_TIMEOUT} seconds"
                state.end_time = time.time()
                state.duration = time.time() - state.start_time

                # Update current state
                self.current_state = state

            except Exception as e:
                logger.exception(f"Workflow execution failed: {str(e)}")

                # Handle any TaskGroup or async gathering errors
                error_message = str(e)
                if hasattr(e, "__cause__") and e.__cause__ is not None:
                    error_message = f"{error_message} - Caused by: {str(e.__cause__)}"

                state.status = "error"
                state.error = error_message
                state.end_time = time.time()
                state.duration = time.time() - state.start_time

                # Update current state
                self.current_state = state

        except Exception as e:
            logger.exception(f"Error in background workflow execution: {str(e)}")

    def get_current_state(self) -> Optional[Dict[str, Any]]:
        """Get the current workflow state."""
        if self.current_state is None:
            return None
        return self.current_state.model_dump()

    def reset_state(self) -> None:
        """Reset the workflow state."""
        self.current_state = None
        logger.info("Workflow state reset")

    async def close(self) -> None:
        """Close resources used by the workflow manager."""
        await self.planner.agent.on_reset(CancellationToken())
        await self.executor.agent.on_reset(CancellationToken())
        await self.verifier.agent.on_reset(CancellationToken())
        logger.info("Workflow manager closed")

    async def _store_assistant_message(self, final_state: WorkflowState) -> None:
        """Store the final assistant message in the database.

        Args:
            final_state: The final workflow state with response
        """
        if not final_state.response or not final_state.conversation_id:
            logger.warning(
                f"Missing response or conversation_id in final state, cannot store message"
            )
            return

        try:
            # Add retry mechanism with exponential backoff
            max_retries = 3
            base_delay = 0.1  # 100ms initial delay

            for attempt in range(max_retries):
                # Get the conversation
                conversation = await Conversation.get_or_none(id=final_state.conversation_id)
                if conversation:
                    break

                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)  # Exponential backoff
                    logger.info(
                        f"Conversation not found, retrying in {delay}s (attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(delay)
                    continue

                # If we get here, we've exhausted our retries
                logger.error(
                    f"Conversation not found after {max_retries} attempts: {final_state.conversation_id}"
                )
                return

            # Find the next sequence number
            next_sequence = await Message.filter(conversation=conversation).count() + 1

            # Create metadata from workflow state
            metadata = {
                "workflow_id": final_state.workflow_id,
                "execution_time": final_state.duration,
                "status": final_state.status,
            }

            # Store assistant message
            response_content = final_state.response
            logger.info(f"Creating assistant message with content: {response_content[:100]}...")
            assistant_message = await Message.create(
                conversation=conversation,
                role="assistant",
                content=response_content,
                sequence=next_sequence,
                message_metadata=metadata,
            )

            logger.info(f"Assistant message stored with ID: {assistant_message.id}")

        except Exception as e:
            logger.error(f"Error storing assistant message: {str(e)}", exc_info=True)
