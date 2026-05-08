"""Memory tool name registry.

The memory tool implementations live on the MCP server (mcp/tools/memory.py).
This module only exports MEMORY_TOOL_NAMES, which the agent graph uses to
suppress these tools from the pending-approval banner (they are transparent
agent operations, not user-visible infrastructure mutations).
"""

MEMORY_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "memory_search",
        "memory_read",
        "memory_list",
        "memory_history",
        "memory_remember",
        "memory_patch",
        "memory_propose_promotion",
    }
)
