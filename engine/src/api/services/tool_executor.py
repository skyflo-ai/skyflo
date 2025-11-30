import json
import logging
import uuid
from typing import Any, Awaitable, Callable, Dict, List, Optional

from .tools_cache import ToolsCache
from .approvals import ApprovalService
from .mcp_client import MCPClient
from .integrations import IntegrationService
from ..config import settings
from ..utils.sanitization import mcp_tools_to_openai_format
from ..integrations.jenkins import filter_jenkins_tools, inject_jenkins_metadata_tool_args
from ..utils.clock import now_ms

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[str, Optional[float]], Awaitable[None]]
EventCallback = Callable[[Dict[str, Any]], Awaitable[None]]


class ToolExecutor:
    def __init__(
        self,
        approvals: Optional[ApprovalService] = None,
        sse_publish: Optional[EventCallback] = None,
        mcp_client: Optional[MCPClient] = None,
        owns_client: bool = True,
    ):
        self.mcp_url = settings.MCP_SERVER_URL
        self.sse_publish = sse_publish
        self._mcp_client: Optional[MCPClient] = mcp_client
        self._owns_client: bool = owns_client if mcp_client is None else False

        self._tools = ToolsCache()
        self._integrations = (
            IntegrationService(mcp_client=self._mcp_client) if mcp_client else IntegrationService()
        )

        if approvals:
            self.approvals = approvals
            self.approvals.tool_metadata_fetcher = self._get_tool_metadata
        else:
            self.approvals = ApprovalService(tool_metadata_fetcher=self._get_tool_metadata)

    async def _get_mcp_client(self) -> MCPClient:
        if self._mcp_client is None:
            self._mcp_client = MCPClient()
            self._owns_client = True
        return self._mcp_client

    def invalidate_tools_cache(self) -> None:
        self._tools.invalidate()

    async def _fetch_tools_from_server(self) -> List[Any]:
        client = await self._get_mcp_client()
        return await client.list_tools_raw()

    async def _get_tool_metadata(self, tool_name: str) -> Optional[Dict[str, Any]]:
        try:
            return await self._tools.get_by_name(tool_name, self._fetch_tools_from_server)
        except Exception as e:
            logger.error(f"Error fetching metadata for tool '{tool_name}': {e}")
            return None

    async def close(self) -> None:
        self._mcp_client = None
        await self.approvals.close()

    async def filter_integrations_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        try:
            jenkins_integration = await self._integrations.get_integration("jenkins")
            jenkins_configured = jenkins_integration is not None
            jenkins_status = jenkins_integration.status if jenkins_integration else None

            tools = filter_jenkins_tools(
                tools=tools, integration_status=jenkins_status, is_configured=jenkins_configured
            )

            return tools
        except Exception as e:
            logger.error(f"Error filtering integration tools: {e}")
            return tools

    async def inject_integration_tool_params(
        self,
        tool_name: str,
        args: Dict[str, Any],
        tool_metadata: Optional[Dict[str, Any]],
        call_id: str,
        tool_title: str,
        run_id: str,
    ) -> tuple[Dict[str, Any], Optional[List[Dict[str, Any]]]]:
        jenkins_integration = await self._integrations.get_integration("jenkins")
        args, jenkins_error = inject_jenkins_metadata_tool_args(
            tool_name=tool_name,
            args=args,
            tool_metadata=tool_metadata,
            integration=jenkins_integration,
        )

        if jenkins_error:
            if self.sse_publish:
                await self.sse_publish(
                    {
                        "type": "tool.error",
                        "call_id": call_id,
                        "tool": tool_name,
                        "title": tool_title,
                        "error": jenkins_error,
                        "run_id": run_id,
                        "timestamp": now_ms(),
                    }
                )
            return args, [{"type": "text", "text": jenkins_error}]

        return args, None

    async def get_llm_compatible_tools(self) -> List[Dict[str, Any]]:
        try:
            all_tools = await self._tools.get_all(self._fetch_tools_from_server)

            all_tools = await self.filter_integrations_tools(all_tools)

            return mcp_tools_to_openai_format({"tools": all_tools})
        except Exception as e:
            logger.error(f"Error preparing OpenAI-compatible tools: {e}")
            try:
                client = await self._get_mcp_client()
                tools_raw = await client.get_tools()

                return mcp_tools_to_openai_format(tools_raw)
            except Exception as inner:
                logger.error(f"Fallback tools fetch failed: {inner}")
                return []

    class ApprovalPending(Exception):
        def __init__(self, call_id: str, tool: str):
            super().__init__(f"Approval pending for {tool} ({call_id})")
            self.call_id = call_id
            self.tool = tool

    async def execute(
        self,
        run_id: str,
        name: str,
        args: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        call_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        call_id = (call_id or str(uuid.uuid4())).strip()

        try:
            tool_metadata = await self._get_tool_metadata(name)
            tool_title = tool_metadata.get("title", name) if tool_metadata else name

            args, integration_error = await self.inject_integration_tool_params(
                tool_name=name,
                args=args,
                tool_metadata=tool_metadata,
                call_id=call_id,
                tool_title=tool_title,
                run_id=run_id,
            )

            if integration_error is not None:
                return integration_error

            validation_error = await self._validate_tool_parameters(name, args, tool_metadata)
            if validation_error:
                return [{"type": "text", "text": f"Tool validation failed: {validation_error}"}]

            needs_approval = await self.approvals.need_approval(name, args)

            if needs_approval:
                decision = None
                try:
                    decision = (context or {}).get("approval_decisions", {}).get(call_id)
                except Exception:
                    decision = None

                if decision is None:
                    if self.sse_publish:
                        await self.sse_publish(
                            {
                                "type": "tool.awaiting_approval",
                                "run_id": run_id,
                                "call_id": call_id,
                                "tool": name,
                                "title": tool_title,
                                "args": args,
                                "context": context or {},
                                "timestamp": now_ms(),
                            }
                        )
                    raise ToolExecutor.ApprovalPending(call_id=call_id, tool=name)
                elif decision is False:
                    if self.sse_publish:
                        await self.sse_publish(
                            {
                                "type": "tool.denied",
                                "call_id": call_id,
                                "tool": name,
                                "title": tool_title,
                                "args": args,
                                "run_id": run_id,
                                "timestamp": now_ms(),
                            }
                        )
                    return [{"type": "text", "text": "Tool call was denied by the user"}]
                else:
                    if self.sse_publish:
                        await self.sse_publish(
                            {
                                "type": "tool.approved",
                                "call_id": call_id,
                                "tool": name,
                                "title": tool_title,
                                "args": args,
                                "run_id": run_id,
                                "timestamp": now_ms(),
                            }
                        )

            mcp_client = await self._get_mcp_client()

            if self.sse_publish:
                await self.sse_publish(
                    {
                        "type": "tool.executing",
                        "call_id": call_id,
                        "tool": name,
                        "title": tool_title,
                        "args": args,
                        "run_id": run_id,
                        "timestamp": now_ms(),
                    }
                )

            result = await mcp_client.call_tool(
                tool_name=name, parameters=args, conversation_id=run_id
            )

            tool_had_error = bool(isinstance(result, dict) and result.get("isError", False))
            if tool_had_error:
                error_message = "Tool execution failed"
                if isinstance(result, dict) and result.get("content"):
                    parts: List[str] = []
                    for block in result["content"]:
                        if isinstance(block, dict) and block.get("type") == "text":
                            parts.append(block.get("text", ""))
                    if parts:
                        error_message = "\n".join(parts)

                if self.sse_publish:
                    await self.sse_publish(
                        {
                            "type": "tool.error",
                            "call_id": call_id,
                            "tool": name,
                            "title": tool_title,
                            "error": error_message,
                            "run_id": run_id,
                            "timestamp": now_ms(),
                        }
                    )
                return [{"type": "text", "text": f"Tool error: {error_message}"}]

            content_blocks: List[Dict[str, Any]] = []
            if isinstance(result, dict):
                if "content" in result:
                    content_blocks = result["content"]
                elif "result" in result:
                    actual = result["result"]
                    if isinstance(actual, str):
                        content_blocks.append({"type": "text", "text": actual})
                    elif isinstance(actual, dict):
                        content_blocks.append(
                            {"type": "text", "text": json.dumps(actual, indent=2)}
                        )
                    elif isinstance(actual, list):
                        for item in actual:
                            if isinstance(item, dict) and "type" in item:
                                content_blocks.append(item)
                            else:
                                content_blocks.append({"type": "text", "text": str(item)})
                    else:
                        content_blocks.append({"type": "text", "text": str(actual)})
                else:
                    content_blocks.append({"type": "text", "text": json.dumps(result, indent=2)})
            else:
                content_blocks.append({"type": "text", "text": str(result)})

            if self.sse_publish:
                await self.sse_publish(
                    {
                        "type": "tool.result",
                        "call_id": call_id,
                        "tool": name,
                        "title": tool_title,
                        "result": content_blocks,
                        "run_id": run_id,
                        "timestamp": now_ms(),
                    }
                )

            return content_blocks

        except ToolExecutor.ApprovalPending as awaiting:
            raise awaiting
        except Exception as e:
            logger.exception(f"Error executing tool {name}: {e}")
            if self.sse_publish:
                await self.sse_publish(
                    {
                        "type": "tool.error",
                        "call_id": call_id,
                        "tool": name,
                        "title": locals().get("title", name),
                        "error": str(e),
                        "run_id": run_id,
                        "timestamp": now_ms(),
                    }
                )
            return [{"type": "text", "text": f"Error executing {name}: {e}"}]

    async def list_tools(self, category: Optional[str] = None) -> Dict[str, Any]:
        try:
            all_tools = await self._tools.get_all(self._fetch_tools_from_server)
            if category:
                c = category.lower()
                filtered = [
                    t
                    for t in all_tools
                    if isinstance(t.get("name"), str) and c in t["name"].lower()
                ]
                return {"tools": filtered}
            return {"tools": all_tools}
        except Exception as e:
            logger.error(f"Error listing tools: {e}")
            return {"tools": [], "error": str(e)}

    async def _validate_tool_parameters(
        self, name: str, args: Dict[str, Any], tool_metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        try:
            tool_schema = tool_metadata or await self._get_tool_metadata(name)
            if not tool_schema:
                return f"Tool '{name}' not found in available tools"

            input_schema = tool_schema.get("inputSchema") or tool_schema.get("input_schema")
            if input_schema and "required" in input_schema:
                required: List[str] = list(input_schema["required"])
                if required:
                    missing = [p for p in required if p not in args]
                    if missing:
                        return f"Missing required parameters: {', '.join(missing)}"

            return None
        except Exception as e:
            logger.error(f"Error validating tool parameters: {e}")
            return f"Parameter validation error: {e}"
