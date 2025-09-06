import logging
import time
from typing import Any, Dict, Literal, Optional, Callable, Awaitable
from ..utils.clock import now_ms

from langgraph.graph import StateGraph, START, END
from langgraph.errors import GraphRecursionError
from ..services.checkpointer import get_checkpointer
from langgraph.checkpoint.memory import MemorySaver

from .state import AgentState
from .model_node import ModelNode
from ..services.tool_executor import ToolExecutor
from ..services.mcp_client import MCPClient
from ..services.approvals import ApprovalService
from ..config import settings
from ..utils.helpers import get_state_value
from ..services.stop_service import clear_stop
from .stop import StopRequested, check_stop

logger = logging.getLogger(__name__)

EventCallback = Callable[[Dict[str, Any]], Awaitable[None]]


async def _check_stop(state: Dict[str, Any]) -> None:
    await check_stop(state)


def route_after_model(state: Dict[str, Any]) -> Literal["gate", "model", "final"]:
    pending_tools = get_state_value(state, "pending_tools", [])

    if pending_tools:
        tool_names = [
            tool.get("name", "unknown") for tool in pending_tools if isinstance(tool, dict)
        ]
        return "gate"

    auto_turns = get_state_value(state, "auto_continue_turns", 0)
    if auto_turns > 0:
        return "model"

    return "final"


def route_from_entry(state: Dict[str, Any]) -> Literal["gate", "model"]:
    pending_tools = get_state_value(state, "pending_tools", [])
    if pending_tools:
        return "gate"
    return "model"


def route_after_gate(state: Dict[str, Any]) -> Literal["model", "final"]:
    if get_state_value(state, "awaiting_approval", False):
        return "final"
    return "model"


class WorkflowGraph:
    def __init__(
        self,
        event_callback: Optional[EventCallback] = None,
    ):
        self.event_callback = event_callback

        self.approval_service = ApprovalService()
        self.mcp_client = MCPClient(event_callback=self.event_callback)
        self.tool_executor = ToolExecutor(
            approvals=self.approval_service,
            sse_publish=self.event_callback,
            mcp_client=self.mcp_client,
            owns_client=False,
        )
        self.model_node = ModelNode(
            event_callback=self.event_callback,
            tools_provider=self.tool_executor.get_openai_compatible_tools,
        )
        self.graph = self._build_graph()
        self.compiled_graph = None
        self.checkpointer = None

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)

        workflow.add_node("entry", self._entry_node)
        workflow.add_node("model", self._model_node)
        workflow.add_node("gate", self._gate_node)
        workflow.add_node("final", self._final_node)

        workflow.add_edge(START, "entry")
        workflow.add_conditional_edges(
            "entry", route_from_entry, {"gate": "gate", "model": "model"}
        )
        workflow.add_conditional_edges(
            "model", route_after_model, {"gate": "gate", "model": "model", "final": "final"}
        )
        workflow.add_conditional_edges(
            "gate", route_after_gate, {"model": "model", "final": "final"}
        )
        workflow.add_edge("final", END)

        return workflow

    async def _compile_graph(self):
        checkpointer = None

        if settings.ENABLE_POSTGRES_CHECKPOINTER:
            try:
                checkpointer = get_checkpointer()
            except Exception as e:
                logger.warning(
                    f"Failed to get shared checkpointer: {e}. Falling back to in-memory checkpointer"
                )
                checkpointer = None

        if checkpointer is None:
            checkpointer = MemorySaver()
            logger.debug("Graph compiled with in-memory checkpointer")

        self.checkpointer = checkpointer

        compiled = self.graph.compile(checkpointer=checkpointer)
        return compiled

    async def _ensure_compiled(self):
        if self.compiled_graph is None:
            self.compiled_graph = await self._compile_graph()

    async def _entry_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        await _check_stop(state)
        if get_state_value(state, "awaiting_approval", False):
            return {"awaiting_approval": False}
        return {}

    async def _model_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        try:
            await _check_stop(state)
            result = await self.model_node(state)

            updated_state = {}
            if "messages" in result:
                updated_state["messages"] = result["messages"]
            if "pending_tools" in result:
                updated_state["pending_tools"] = result["pending_tools"]
            if "error" in result:
                updated_state["error"] = result["error"]

            return updated_state

        except Exception as e:
            logger.exception(f"Error in model node: {str(e)}")
            return {"error": str(e)}

    async def _gate_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        try:
            await _check_stop(state)

            pending_tools = get_state_value(state, "pending_tools", [])
            if not pending_tools:
                return {"pending_tools": [], "suppress_pending_event": False}

            try:
                suppress_pending_event = get_state_value(state, "suppress_pending_event", False)
                if self.event_callback and not suppress_pending_event:
                    pending_payload = []
                    for tool_call in pending_tools:
                        try:
                            tool_name = tool_call.get("name", "unknown")
                            tool_call_id = tool_call.get("id")
                            tool_args = (
                                tool_call.get("args", {}) if isinstance(tool_call, dict) else {}
                            )

                            title_value = tool_name
                            try:
                                metadata = await self.tool_executor._get_tool_metadata(tool_name)
                                if metadata and isinstance(metadata, dict):
                                    title_value = metadata.get("title", tool_name)
                            except Exception:
                                title_value = tool_name

                            requires_approval_value = False
                            try:
                                requires_approval_value = await self.approval_service.need_approval(
                                    tool_name, tool_args
                                )
                            except Exception:
                                requires_approval_value = True

                            pending_payload.append(
                                {
                                    "call_id": tool_call_id,
                                    "tool": tool_name,
                                    "title": title_value,
                                    "args": tool_args,
                                    "requires_approval": requires_approval_value,
                                    "timestamp": now_ms(),
                                }
                            )
                        except Exception:
                            continue

                    await self.event_callback(
                        {
                            "type": "tools.pending",
                            "run_id": get_state_value(state, "run_id", "unknown"),
                            "tools": pending_payload,
                            "timestamp": now_ms(),
                        }
                    )
            except Exception:
                pass

            tool_messages = []

            for idx, tool_call in enumerate(pending_tools):
                try:
                    tool_name = tool_call["name"]
                    tool_call_id = tool_call.get("id")
                    tool_args = tool_call.get("args", {}) if isinstance(tool_call, dict) else {}

                    tool_results = await self.tool_executor.execute(
                        run_id=get_state_value(state, "run_id", "unknown"),
                        name=tool_name,
                        args=tool_args,
                        context={
                            "conversation_id": get_state_value(state, "conversation_id"),
                            "approval_decisions": get_state_value(state, "approval_decisions", {}),
                        },
                        call_id=tool_call_id,
                    )

                    result_content = ""
                    for block in tool_results:
                        if block.get("type") == "text":
                            result_content += block.get("text", "")
                        else:
                            result_content += str(block)

                    tool_message = {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "name": tool_name,
                        "content": result_content,
                    }
                    tool_messages.append(tool_message)

                except ToolExecutor.ApprovalPending as awaiting:
                    remaining_tools = pending_tools[idx:]
                    return {
                        "messages": tool_messages,
                        "pending_tools": remaining_tools,
                        "awaiting_approval": True,
                        "auto_continue_turns": 0,
                        "suppress_pending_event": False,
                    }
                except Exception as tool_error:
                    logger.exception(
                        f"Error executing tool {tool_call.get('name', 'unknown')}: {str(tool_error)}"
                    )

                    error_message = {
                        "role": "tool",
                        "tool_call_id": tool_call.get("id"),
                        "name": tool_call.get("name", "system"),
                        "content": f"Error executing tool {tool_call.get('name', 'unknown')}: {str(tool_error)}",
                    }
                    tool_messages.append(error_message)

            return {
                "messages": tool_messages,
                "pending_tools": [],
                "awaiting_approval": False,
                "suppress_pending_event": False,
            }

        except Exception as e:
            logger.exception(f"Error in gate node: {str(e)}")

            error_message = {
                "role": "assistant",
                "name": None,
                "content": f"Error in tool execution gate: {str(e)}",
            }

            return {
                "messages": [error_message],
                "pending_tools": [],
                "error": str(e),
                "suppress_pending_event": False,
            }

    async def _final_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        end_time = time.time()
        start_time = get_state_value(state, "start_time", end_time)
        duration = end_time - start_time

        if self.event_callback:
            await self.event_callback(
                {
                    "type": "completed",
                    "status": "completed",
                    "run_id": get_state_value(state, "run_id"),
                    "duration": duration,
                }
            )

        return {"done": True, "end_time": end_time, "duration": duration}

    async def invoke(self, initial_state: Dict[str, Any], **kwargs):
        try:
            await self._ensure_compiled()
            try:
                await self.mcp_client._ensure_client()
            except Exception:
                pass

            start_time_value = get_state_value(initial_state, "start_time")
            if start_time_value is None:
                current_time = time.time()

                if hasattr(initial_state, "start_time"):
                    setattr(initial_state, "start_time", current_time)
                elif hasattr(initial_state, "__setitem__"):
                    initial_state["start_time"] = current_time

            config = kwargs.get("config", {})
            if "configurable" not in config:
                thread_id = get_state_value(initial_state, "conversation_id") or get_state_value(
                    initial_state, "run_id", "default"
                )
                config["configurable"] = {"thread_id": thread_id}
                config["recursion_limit"] = settings.LLM_MAX_ITERATIONS
                kwargs["config"] = config

            try:
                result = await self.compiled_graph.ainvoke(initial_state, **kwargs)
                return result
            except StopRequested:
                if self.event_callback:
                    await self.event_callback(
                        {
                            "type": "completed",
                            "status": "stopped",
                            "run_id": get_state_value(initial_state, "run_id"),
                        }
                    )
                try:
                    await clear_stop(get_state_value(initial_state, "conversation_id"))
                except Exception:
                    pass
                return {"done": True, "stopped": True}
            except GraphRecursionError:
                if self.event_callback:
                    await self.event_callback(
                        {
                            "type": "workflow.error",
                            "run_id": get_state_value(initial_state, "run_id"),
                            "error": f"The AI Agent has reached the maximum number of iterations of {settings.LLM_MAX_ITERATIONS} for the current prompt. You can continue the conversation. If you want to update the max iterations, update the LLM_MAX_ITERATIONS environment variable.",
                        }
                    )
            except Exception as e:
                if self.event_callback:
                    await self.event_callback(
                        {
                            "type": "workflow.error",
                            "run_id": get_state_value(initial_state, "run_id"),
                            "error": f"An unknown error occurred while executing the workflow: {str(e)}",
                        }
                    )

        except Exception as e:
            if self.event_callback:
                await self.event_callback(
                    {
                        "type": "workflow.error",
                        "run_id": get_state_value(initial_state, "run_id"),
                        "error": f"An unknown error occurred while executing the workflow: {str(e)}",
                    }
                )

    async def close(self):
        try:
            await self.tool_executor.close()
            await self.approval_service.close()
            if hasattr(self, "mcp_client") and self.mcp_client:
                await self.mcp_client.close()

            if self.checkpointer and hasattr(self.checkpointer, "aclose"):
                await self.checkpointer.aclose()
            elif self.checkpointer and hasattr(self.checkpointer, "conn"):
                if hasattr(self.checkpointer.conn, "aclose"):
                    await self.checkpointer.conn.aclose()

        except Exception as e:
            logger.error(f"Error closing workflow resources: {str(e)}")


def build_graph(
    event_callback: Optional[EventCallback] = None,
) -> WorkflowGraph:
    return WorkflowGraph(event_callback=event_callback)
