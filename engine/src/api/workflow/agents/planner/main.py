"""Core implementation of the planner agent."""

import asyncio
import json
import uuid
import logging
from typing import Dict, Any, Mapping, Optional, Callable, Awaitable, List
from datetime import datetime
from collections import defaultdict
from api.workflow.agents.base import BaseAgent
from api.config import settings
from api.services.mcp_client import MCPClient
from api.workflow.agents.planner.types import PlannerState, PlannerConfig, ToolDependency
from api.workflow.agents.planner.prompt_templates import (
    PLANNER_SYSTEM_MESSAGE,
    ANALYZE_QUERY_PROMPT,
    DISCOVERY_SYSTEM_PROMPT,
    DISCOVERY_QUERY_PROMPT,
)
from api.llm_schemas import DiscoveryPlan, ExecutionPlan

logger = logging.getLogger(__name__)


class PlannerAgent(BaseAgent):
    """Agent responsible for planning the execution strategy."""

    component_type = "skyflo.agents.PlannerAgent"
    component_config_schema = PlannerConfig

    def __init__(
        self,
        name: str = "planner",
        system_message: str = None,
        model_context=None,
        description: Optional[str] = None,
        event_callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
    ):
        """Initialize the planner agent."""
        system_message = system_message or PLANNER_SYSTEM_MESSAGE
        super().__init__(
            name=name,
            system_message=system_message,
            model_context=model_context,
            description=description or "Skyflo planner agent that creates execution strategies",
        )
        self._model_context = model_context or {}  # Store model_context as instance variable
        self.mcp_client = MCPClient(event_callback=event_callback)
        self._state = PlannerState()
        self._config = PlannerConfig()
        self.event_callback = event_callback

    def _normalize_plan_format(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize plan format by converting parameters from list to dictionary format.

        Args:
            plan: The plan with parameters in list format

        Returns:
            The plan with parameters converted to dictionary format
        """
        if not isinstance(plan, dict):
            return plan

        normalized_plan = plan.copy()

        # Convert parameters in steps
        if "steps" in normalized_plan and isinstance(normalized_plan["steps"], list):
            for step in normalized_plan["steps"]:
                if isinstance(step, dict):
                    # Set default values for step properties if not present
                    if "required" not in step:
                        step["required"] = True
                    if "recursive" not in step:
                        step["recursive"] = False
                    if "discovery_step" not in step:
                        step["discovery_step"] = False

                    # Convert parameters if needed
                    if "parameters" in step:
                        params = step["parameters"]
                        if isinstance(params, list):
                            # Convert from [{"name": "key", "value": "val"}] to {"key": "val"}
                            step["parameters"] = {
                                param.get("name"): param.get("value")
                                for param in params
                                if isinstance(param, dict) and "name" in param and "value" in param
                            }

        return normalized_plan

    async def _build_tool_dependency_graph(self) -> Dict[str, ToolDependency]:
        """Build a graph of tool dependencies."""
        tools_response = await self.mcp_client.get_tools()
        graph = {}

        if not isinstance(tools_response, dict) or "tools" not in tools_response:
            logger.error(f"Unexpected tools response format: {type(tools_response)}")
            return graph

        tools_list = tools_response["tools"]
        if not isinstance(tools_list, list):
            logger.error(f"Unexpected tools list format: {type(tools_list)}")
            return graph

        for tool in tools_list:
            if not isinstance(tool, dict) or "name" not in tool:
                logger.warning(f"Skipping invalid tool format: {tool}")
                continue

            deps = ToolDependency(
                tool=tool["name"],
                provides=tool.get("capabilities", []),
                weight=tool.get("complexity", 1),
            )
            graph[tool["name"]] = deps

        # Analyze dependencies
        for tool_name, deps in graph.items():
            for other_name, other_deps in graph.items():
                if tool_name != other_name:
                    # If this tool's capabilities are needed by another tool
                    if any(cap in other_deps.provides for cap in deps.provides):
                        deps.required_by.append(other_name)

        self._state.tool_graph = graph
        return graph

    async def _minimize_tool_set(
        self, required_tools: List[str], graph: Dict[str, ToolDependency]
    ) -> List[str]:
        """Minimize the set of tools needed while maintaining functionality."""
        if not graph:
            graph = await self._build_tool_dependency_graph()

        # Build capability map
        capability_map = defaultdict(set)
        for tool_name, deps in graph.items():
            for cap in deps.provides:
                capability_map[cap].add(tool_name)

        # Get required capabilities
        required_capabilities = set()
        for tool in required_tools:
            if tool in graph:
                required_capabilities.update(graph[tool].provides)

        # Find minimal set of tools that provide all capabilities
        selected_tools = set()
        remaining_capabilities = required_capabilities.copy()

        while remaining_capabilities:
            # Find tool that provides most remaining capabilities with lowest weight
            best_tool = None
            best_score = -1

            for tool_name, deps in graph.items():
                if tool_name in selected_tools:
                    continue

                provides_count = len([c for c in deps.provides if c in remaining_capabilities])
                if provides_count > 0:
                    score = provides_count / deps.weight
                    if score > best_score:
                        best_score = score
                        best_tool = tool_name

            if not best_tool:
                break

            selected_tools.add(best_tool)
            remaining_capabilities -= set(graph[best_tool].provides)

        return list(selected_tools)

    async def create_discovery_plan(
        self, query: str, conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a discovery plan to gather necessary cluster information.

        Args:
            query: The user's natural language query
            conversation_id: Optional conversation ID for context

        Returns:
            Dict containing the discovery plan
        """
        logger.debug(f"Creating discovery plan for query: {query}")
        await asyncio.sleep(0.25)

        try:
            # Emit event that we're starting discovery planning
            if self.event_callback:
                await self.event_callback(
                    {
                        "type": "discovery_planning",
                        "agent": "planner",
                        "message": "Analyzing your request to determine what information to gather",
                        "phase": "discovery",
                        "state": "plan",
                        "conversation_id": conversation_id,
                        "details": {
                            "query": query[:100] + "..." if len(query) > 100 else query,
                            "timestamp": datetime.now().isoformat(),
                            "conversation_id": conversation_id,
                        },
                        "data": {
                            "progress": 0.1,
                            "message": "Creating discovery plan",
                            "conversation_id": conversation_id,
                        },
                    }
                )

            # Get available tools
            available_tools = await self.mcp_client.get_tools()
            logger.debug(f"Received tools data: {available_tools}")

            if not isinstance(available_tools, dict):
                return await self._handle_planning_error(
                    "Invalid tools data format from MCP server", query
                )

            if "tools" not in available_tools:
                return await self._handle_planning_error(
                    "No tools data received from MCP server", query
                )

            tools_list = available_tools["tools"]
            if not isinstance(tools_list, list):
                return await self._handle_planning_error(
                    "Invalid tools list format from MCP server", query
                )

            if not tools_list:
                return await self._handle_planning_error(
                    "No tools are currently available from the MCP server", query
                )

            # Extract tool information with detailed parameter info
            tool_info = []
            for tool in tools_list:
                if isinstance(tool, dict) and "name" in tool and "category" in tool:
                    # Process parameters to make requirements clear
                    parameters = []
                    for param in tool.get("parameters", []):
                        param_info = {
                            "name": param.get("name", ""),
                            "type": param.get("type", ""),
                            "description": param.get("description", ""),
                            "required": param.get("required", False),
                            "default": param.get("default"),
                            "aliases": param.get("aliases", []),
                        }
                        parameters.append(param_info)

                    tool_info.append(
                        {
                            "name": tool["name"],
                            "category": tool["category"],
                            "description": tool.get("description", ""),
                            "parameters": parameters,
                        }
                    )
                else:
                    logger.warning(f"Skipping invalid tool format: {tool}")

            if not tool_info:
                return await self._handle_planning_error("No valid tool definitions found", query)

            logger.debug(f"Found {len(tool_info)} valid tools for discovery")

            # Build prompt for the LLM
            prompt_messages = [
                {"role": "system", "content": DISCOVERY_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": DISCOVERY_QUERY_PROMPT.format(
                        tools_json=json.dumps(tool_info, indent=2), query=query
                    ),
                },
            ]

            # Get structured response from the LLM using the DiscoveryPlan schema
            discovery_plan = await self._get_structured_llm_response(
                prompt_messages, DiscoveryPlan, settings.OPENAI_PLANNER_TEMPERATURE
            )
            logger.debug(f"LLM structured discovery response: {discovery_plan}")

            # Normalize the plan format (convert parameters from list to dict)
            discovery_plan = self._normalize_plan_format(discovery_plan)

            # Add plan metadata
            discovery_plan["plan_id"] = str(uuid.uuid4())

            # Assign unique IDs to each step
            if "steps" in discovery_plan and isinstance(discovery_plan["steps"], list):
                for step in discovery_plan["steps"]:
                    if isinstance(step, dict):
                        step["step_id"] = str(uuid.uuid4())

            logger.debug(f"Discovery plan generated: {discovery_plan}")

            discovery_plan["status"] = "ready"
            discovery_plan["type"] = "discovery"

            # Cache the discovery plan
            self._cache_plan(f"discovery_{query}", discovery_plan)
            await asyncio.sleep(0.25)

            # Emit event that the discovery plan was generated
            if self.event_callback:
                await self.event_callback(
                    {
                        "type": "discovery_plan_generated",
                        "agent": "planner",
                        "message": f"Discovery plan created with {len(discovery_plan.get('steps', []))} steps",
                        "phase": "discovery",
                        "state": "plan",
                        "conversation_id": conversation_id,
                        "details": {
                            "plan": discovery_plan,
                            "plan_id": discovery_plan["plan_id"],
                            "step_count": len(discovery_plan.get("steps", [])),
                            "discovery_intent": discovery_plan.get(
                                "discovery_intent", "Unknown intent"
                            ),
                            "timestamp": datetime.now().isoformat(),
                            "conversation_id": conversation_id,
                        },
                        "data": {
                            "progress": 0.2,
                            "message": "Discovery plan generation complete",
                            "conversation_id": conversation_id,
                        },
                    }
                )

            logger.debug(f"Generated discovery plan: {discovery_plan}")
            return discovery_plan

        except Exception as e:
            logger.error(f"Error in create_discovery_plan: {str(e)}", exc_info=True)
            return await self._handle_planning_error(str(e), query)

    async def analyze_query(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        discovery_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Analyze a user query and create an execution plan.

        Args:
            query: The user's natural language query
            conversation_id: Optional conversation ID for context
            discovery_context: Optional context from discovery phase

        Returns:
            Dict containing the execution plan
        """
        logger.debug(f"Analyzing query with discovery context: {query}")

        try:
            # Get available tools
            available_tools = await self.mcp_client.get_tools()
            logger.debug(f"Received tools data: {available_tools}")

            if not isinstance(available_tools, dict):
                return await self._handle_planning_error(
                    "Invalid tools data format from MCP server", query
                )

            if "tools" not in available_tools:
                return await self._handle_planning_error(
                    "No tools data received from MCP server", query
                )

            tools_list = available_tools["tools"]
            if not isinstance(tools_list, list):
                return await self._handle_planning_error(
                    "Invalid tools list format from MCP server", query
                )

            if not tools_list:
                return await self._handle_planning_error(
                    "No tools are currently available from the MCP server", query
                )

            # Extract tool information with detailed parameter info
            tool_info = []
            for tool in tools_list:
                if isinstance(tool, dict) and "name" in tool and "category" in tool:
                    # Process parameters to make requirements clear
                    parameters = []
                    for param in tool.get("parameters", []):
                        param_info = {
                            "name": param.get("name", ""),
                            "type": param.get("type", ""),
                            "description": param.get("description", ""),
                            "required": param.get("required", False),
                            "default": param.get("default"),
                            "aliases": param.get("aliases", []),
                        }
                        parameters.append(param_info)

                    tool_info.append(
                        {
                            "name": tool["name"],
                            "category": tool["category"],
                            "description": tool.get("description", ""),
                            "parameters": parameters,
                        }
                    )
                else:
                    logger.warning(f"Skipping invalid tool format: {tool}")

            if not tool_info:
                return await self._handle_planning_error("No valid tool definitions found", query)

            logger.debug(f"Found {len(tool_info)} valid tools")

            # Build prompt for the LLM, now including discovery context
            prompt_messages = [
                {"role": "system", "content": self.system_message},
                {
                    "role": "user",
                    "content": ANALYZE_QUERY_PROMPT.format(
                        tools_json=json.dumps(tool_info, indent=2),
                        query=query,
                        discovery_context=(
                            json.dumps(discovery_context, indent=2)
                            if discovery_context
                            else "No discovery context available"
                        ),
                    ),
                },
            ]

            # Get structured response from the LLM using the ExecutionPlan schema
            plan = await self._get_structured_llm_response(
                prompt_messages, ExecutionPlan, settings.OPENAI_PLANNER_TEMPERATURE
            )
            logger.debug(f"LLM structured execution plan response: {plan}")

            # Normalize the plan format (convert parameters from list to dict)
            plan = self._normalize_plan_format(plan)

            # Add plan metadata
            plan["plan_id"] = str(uuid.uuid4())

            # Assign unique IDs to each step
            if "steps" in plan and isinstance(plan["steps"], list):
                for step in plan["steps"]:
                    if isinstance(step, dict):
                        step["step_id"] = str(uuid.uuid4())

            plan["status"] = "ready"

            logger.debug(f"Main plan generated: {plan}")

            # Cache the plan
            self._cache_plan(query, plan)
            await asyncio.sleep(0.25)
            # Emit event that the plan was generated
            if self.event_callback:
                await self.event_callback(
                    {
                        "type": "plan_generated",
                        "agent": "planner",
                        "message": f"Execution plan created with {len(plan.get('steps', []))} steps",
                        "phase": "planning",
                        "state": "plan",
                        "conversation_id": conversation_id,
                        "details": {
                            "plan": plan,
                            "plan_id": plan["plan_id"],
                            "step_count": len(plan.get("steps", [])),
                            "intent": plan.get("intent", "Unknown intent"),
                            "timestamp": datetime.now().isoformat(),
                            "conversation_id": conversation_id,
                        },
                        "data": {
                            "progress": 0.25,
                            "message": "Plan generation complete",
                            "conversation_id": conversation_id,
                        },
                    }
                )

            logger.debug(f"Generated optimized plan: {plan}")
            return plan

        except Exception as e:
            logger.error(f"Error in analyze_query: {str(e)}", exc_info=True)
            return await self._handle_planning_error(str(e), query)

    async def _handle_planning_error(
        self, error_message: str, query: str, response_text: str = None
    ) -> Dict[str, Any]:
        """Handle errors during plan generation."""
        logger.error(f"Planning error: {error_message}")
        error_plan = {
            "query": query,
            "intent": "Error occurred during planning",
            "steps": [],
            "validation_criteria": [],
            "context": {
                "requires_verification": False,
                "additional_context": f"Error: {error_message}",
                "error_details": response_text if response_text else None,
            },
            "plan_id": str(uuid.uuid4()),
            "status": "error",
            "error": error_message,
        }
        return error_plan

    def _cache_plan(self, query: str, plan: Dict[str, Any]):
        """Cache a generated plan."""
        try:
            # Get the max cache size from the config schema
            max_cache_size = 100  # Default value if config access fails

            # Try to get from config if available
            if hasattr(self.component_config_schema, "max_plan_cache_size"):
                if hasattr(self.component_config_schema.max_plan_cache_size, "default"):
                    max_cache_size = self.component_config_schema.max_plan_cache_size.default
                else:
                    max_cache_size = self.component_config_schema.max_plan_cache_size

            # Implement LRU-style caching
            if len(self._state.cached_plans) >= max_cache_size:
                # Remove oldest entry
                oldest_query = next(iter(self._state.cached_plans))
                del self._state.cached_plans[oldest_query]

            self._state.cached_plans[query] = plan
        except Exception as e:
            logger.warning(f"Error in caching plan: {str(e)}")
            # Continue without caching if there's an error
            pass

    async def save_state(self) -> Mapping[str, Any]:
        """Save planner agent state."""
        base_state = await super().save_state()
        state = PlannerState(
            inner_state=base_state.get("inner_state", {}),
            tool_graph=self._state.tool_graph,
            cached_plans=self._state.cached_plans,
        )
        return state.model_dump()

    async def load_state(self, state: Mapping[str, Any]) -> None:
        """Load planner agent state."""
        await super().load_state(state)
        self._state = PlannerState(**state)
