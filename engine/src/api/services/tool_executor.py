import json
import logging
import uuid
from typing import Any, Awaitable, Callable, Dict, List, Optional

from ..config import settings
from ..integrations.jenkins import filter_jenkins_tools, inject_jenkins_metadata_tool_args
from ..utils.clock import now_ms
from ..utils.sanitization import mcp_tools_to_openai_format
from .approvals import ApprovalService
from .integrations import IntegrationService
from .mcp_client import MCPClient
from .tools_cache import ToolsCache

logger = logging.getLogger(__name__)

AVAILABLE_TOOLSETS = ("k8s", "helm", "argo", "jenkins")

LOAD_TOOLSET_TOOL: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "load_toolset",
        "description": (
            "Load additional tool categories into the current session. "
            "By default only read-only Kubernetes tools are available. "
            "Call this to load Helm, Argo Rollouts, or Jenkins tools, "
            "or to enable write/mutation operations for any toolset. "
            "Newly loaded tools are not callable in the same response as "
            "load_toolset. They become available on the next model turn."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "toolset": {
                    "type": "string",
                    "enum": list(AVAILABLE_TOOLSETS),
                    "description": "The toolset category to load.",
                },
                "include_write_tools": {
                    "type": "boolean",
                    "description": (
                        "Set to true to include write/mutation tools "
                        "(apply, delete, scale, patch, install, etc.). "
                        "Leave false for read-only operations."
                    ),
                },
            },
            "required": ["toolset", "include_write_tools"],
        },
    },
}


def _resolve_tool_tag(tool: Dict[str, Any]) -> Optional[str]:
    tags = tool.get("tags")
    if isinstance(tags, list) and tags:
        return tags[0]

    meta = tool.get("meta") or {}
    fastmcp = meta.get("_fastmcp") or {}
    fm_tags = fastmcp.get("tags")
    if isinstance(fm_tags, list) and fm_tags:
        return fm_tags[0]

    name = tool.get("name", "")
    if isinstance(name, str):
        if name.startswith("k8s_") or name == "wait_for_x_seconds":
            return "k8s"
        if name.startswith("helm_"):
            return "helm"
        if name.startswith("argo_"):
            return "argo"
        if name.startswith("jenkins_"):
            return "jenkins"

    return None


def _is_read_only(tool: Dict[str, Any]) -> bool:
    annotations = tool.get("annotations") or {}
    return bool(annotations.get("readOnlyHint", False))


ALLOWED_TOOL_TAGS = frozenset(AVAILABLE_TOOLSETS)


def filter_tools_by_loaded_toolsets(
    tools: List[Dict[str, Any]],
    loaded_toolsets: Dict[str, bool],
) -> List[Dict[str, Any]]:
    filtered = []
    for tool in tools:
        tag = _resolve_tool_tag(tool)
        if tag is None or tag not in ALLOWED_TOOL_TAGS:
            continue

        if tag not in loaded_toolsets:
            continue

        include_write = loaded_toolsets[tag]
        if include_write or _is_read_only(tool):
            filtered.append(tool)

    return filtered


ProgressCallback = Callable[[str, Optional[float]], Awaitable[None]]
EventCallback = Callable[[Dict[str, Any]], Awaitable[None]]


class ToolExecutor:
    def __init__(
        self,
        approvals: Optional[ApprovalService] = None,
        sse_publish: Optional[EventCallback] = None,
        mcp_client: Optional[MCPClient] = None,
        owns_client: bool = True,
        tools_cache: Optional[ToolsCache] = None,
    ):
        self.mcp_url = settings.MCP_SERVER_URL
        self.sse_publish = sse_publish
        self._mcp_client: Optional[MCPClient] = mcp_client
        self._owns_client: bool = owns_client if mcp_client is None else False

        self._tools = tools_cache or ToolsCache()
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

    async def get_llm_compatible_tools(
        self, loaded_toolsets: Optional[Dict[str, bool]] = None
    ) -> List[Dict[str, Any]]:
        try:
            all_tools = await self._tools.get_all(self._fetch_tools_from_server)

            all_tools = await self.filter_integrations_tools(all_tools)

            if loaded_toolsets is not None:
                all_tools = filter_tools_by_loaded_toolsets(all_tools, loaded_toolsets)

            openai_tools = mcp_tools_to_openai_format({"tools": all_tools})
            openai_tools.append(LOAD_TOOLSET_TOOL)

            logger.debug(f"Tools provided: {len(openai_tools)} (toolsets={loaded_toolsets})")

            return openai_tools
        except Exception as e:
            logger.error(f"Error preparing OpenAI-compatible tools: {e}")
            try:
                client = await self._get_mcp_client()
                tools_raw = await client.get_tools()

                raw_list = (
                    tools_raw.get("tools", [])
                    if isinstance(tools_raw, dict)
                    else tools_raw
                    if isinstance(tools_raw, list)
                    else []
                )
                if loaded_toolsets is not None:
                    raw_list = filter_tools_by_loaded_toolsets(raw_list, loaded_toolsets)
                openai_tools = mcp_tools_to_openai_format({"tools": raw_list})
                openai_tools.append(LOAD_TOOLSET_TOOL)
                return openai_tools
            except Exception as inner:
                logger.error(f"Fallback tools fetch failed: {inner}")
                return [LOAD_TOOLSET_TOOL]

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
                        "title": locals().get("tool_title", name),
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
