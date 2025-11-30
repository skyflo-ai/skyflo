import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from ..config import settings

logger = logging.getLogger(__name__)


class MCPClient:
    def __init__(self):
        self.mcp_url = settings.MCP_SERVER_URL.rstrip("/")

    def _get_client(self) -> Client:
        transport = StreamableHttpTransport(url=self.mcp_url)
        return Client(transport)

    async def __aenter__(self) -> "MCPClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        pass

    async def list_tools_raw(self) -> List[Dict[str, Any]]:
        client = self._get_client()
        async with client:
            tools = await client.list_tools()
            return [t.model_dump() for t in tools]

    def _get_tool_name(self, tool: Any) -> str:
        """Safely extract tool name from dict or object."""
        if isinstance(tool, dict):
            return str(tool.get("name", ""))
        return str(getattr(tool, "name", ""))

    async def get_tools(self, category: Optional[str] = None) -> Dict[str, Any]:
        try:
            tools = await self.list_tools_raw()
            if category:
                c = category.lower()
                tools = [t for t in tools if c in self._get_tool_name(t).lower()]
            return {"tools": tools}
        except Exception as e:
            logger.error(f"Error fetching tools: {e}")
            return {"tools": []}

    def _parse_content_item(self, content_item: Any) -> Tuple[Dict[str, Any], bool]:
        """Parse a single content item and return (parsed_dict, is_error)."""
        cd = content_item.model_dump() if hasattr(content_item, "model_dump") else content_item

        if cd.get("type") != "text":
            return cd, False

        text_content = cd.get("text", "")

        # Check if text_content is already a dict with output/error format
        if isinstance(text_content, dict) and "output" in text_content and "error" in text_content:
            return {
                "type": "text",
                "text": text_content.get("output", ""),
            }, bool(text_content.get("error"))

        # Try parsing as JSON string
        if isinstance(text_content, str):
            try:
                parsed = json.loads(text_content)
                if isinstance(parsed, dict) and "output" in parsed and "error" in parsed:
                    return {
                        "type": "text",
                        "text": parsed.get("output", text_content),
                    }, bool(parsed.get("error"))
            except (json.JSONDecodeError, TypeError, ValueError):
                pass

        return cd, False

    async def call_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        action: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
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

            client = self._get_client()
            async with client:
                result = await client.call_tool_mcp(name=tool_name, arguments=inferred_parameters)

                is_error = result.isError or False
                content_blocks: List[Dict[str, Any]] = []

                for content_item in result.content:
                    parsed_item, item_is_error = self._parse_content_item(content_item)
                    is_error = is_error or item_is_error
                    content_blocks.append(parsed_item)

                return {
                    "content": content_blocks,
                    "isError": is_error,
                }

        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            raise
