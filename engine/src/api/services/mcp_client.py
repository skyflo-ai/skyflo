import logging
from contextlib import AsyncExitStack
from typing import Any, Awaitable, Callable, Dict, List, Optional

from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from mcp.types import CallToolResult, ListToolsResult, Tool

from ..config import settings

logger = logging.getLogger(__name__)


class MCPClient:
    def __init__(
        self, event_callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None
    ):
        self.base_url = settings.MCP_SERVER_URL.rstrip("/")
        self.sse_url = f"{self.base_url}/sse"
        self.session: Optional[ClientSession] = None
        self.exit_stack: Optional[AsyncExitStack] = None
        self.event_callback = event_callback

    async def _ensure_client(self) -> None:
        if self.session:
            return
        try:
            self.exit_stack = AsyncExitStack()
            read, write = await self.exit_stack.enter_async_context(sse_client(self.sse_url))
            self.session = await self.exit_stack.enter_async_context(ClientSession(read, write))
            init_result = await self.session.initialize()
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            await self.close()
            raise

    async def close(self) -> None:
        try:
            if self.exit_stack:
                try:
                    await self.exit_stack.aclose()
                except Exception as close_error:
                    msg = str(close_error).lower()
                    if "cancel scope" in msg or "different task" in msg or "task scope" in msg:
                        await self._manual_cleanup()
                    else:
                        raise close_error
        except Exception as e:
            logger.error(f"Error closing MCP client: {e}")
        finally:
            self.session = None
            self.exit_stack = None

    async def _manual_cleanup(self) -> None:
        if self.session:
            if hasattr(self.session, "close"):
                await self.session.close()
            elif hasattr(self.session, "__aexit__"):
                await self.session.__aexit__(None, None, None)

    async def __aenter__(self) -> "MCPClient":
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def list_tools_raw(self) -> List[Tool]:
        await self._ensure_client()
        result: ListToolsResult = await self.session.list_tools()
        return result.tools

    async def get_tools(self, category: Optional[str] = None) -> Dict[str, Any]:
        try:
            tools = await self.list_tools_raw()
            if category:
                c = category.lower()
                tools = [t for t in tools if c in t.name.lower()]
            return {"tools": [t.model_dump() for t in tools]}
        except Exception as e:
            logger.error(f"Error fetching tools: {e}")
            return {"tools": []}

    async def call_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        action: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        await self._ensure_client()

        try:
            inferred_parameters = parameters.copy()
            if (
                action
                and tool_name == "get_resources"
                and "resource_type" not in inferred_parameters
            ):
                inferred_parameters["resource_type"] = {
                    "get_pods": "pod",
                    "get_deployments": "deployment",
                    "get_services": "service",
                    "get_namespaces": "namespace",
                    "get_nodes": "node",
                }.get(action, inferred_parameters.get("resource_type"))

            result: CallToolResult = await self.session.call_tool(
                name=tool_name, arguments=inferred_parameters
            )

            is_error = False
            content_blocks: List[Dict[str, Any]] = []

            for content in result.content:
                cd = content.model_dump()
                if cd.get("type") == "text":
                    text_content = cd.get("text", "")
                    if (
                        isinstance(text_content, Dict)
                        and "output" in text_content
                        and "error" in text_content
                    ):
                        is_error = bool(text_content.get("error")) or is_error
                        content_blocks.append(
                            {"type": "text", "text": text_content.get("output", "")}
                        )
                    else:
                        try:
                            import json

                            if isinstance(text_content, str):
                                parsed = json.loads(text_content)
                                if (
                                    isinstance(parsed, Dict)
                                    and "output" in parsed
                                    and "error" in parsed
                                ):
                                    is_error = bool(parsed.get("error")) or is_error
                                    content_blocks.append(
                                        {"type": "text", "text": parsed.get("output", text_content)}
                                    )
                                else:
                                    content_blocks.append(cd)
                            else:
                                content_blocks.append(cd)
                        except (json.JSONDecodeError, TypeError, ValueError):
                            content_blocks.append(cd)
                else:
                    content_blocks.append(cd)

            result_dict = {
                "content": content_blocks,
                "isError": is_error or (getattr(result, "isError", False)),
            }
            return result_dict

        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            raise
