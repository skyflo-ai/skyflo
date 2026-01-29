"""Type definitions for MCP tools."""

from typing_extensions import TypedDict


class ToolOutput(TypedDict):
    """Structured output from tool commands."""

    output: str
    error: bool
