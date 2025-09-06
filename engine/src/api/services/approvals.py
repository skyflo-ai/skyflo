import logging
from typing import Dict, Any, Optional, Callable, Awaitable

logger = logging.getLogger(__name__)

ToolMetadataFetcher = Callable[[str], Awaitable[Optional[Dict[str, Any]]]]


class ApprovalService:
    def __init__(self, tool_metadata_fetcher: Optional[ToolMetadataFetcher] = None):
        self.tool_metadata_fetcher = tool_metadata_fetcher

    async def close(self):
        return

    async def need_approval(self, tool: str, args: Dict[str, Any]) -> bool:
        try:
            if not self.tool_metadata_fetcher:
                return True

            tool_metadata = await self.tool_metadata_fetcher(tool)
            if not tool_metadata:
                return True

            annotations = tool_metadata.get("annotations", {})
            read_only_hint = annotations.get("readOnlyHint", False)
            requires_approval = not read_only_hint

            return requires_approval

        except Exception:
            return True
