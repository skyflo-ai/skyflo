"""Tools API endpoints for Skyflo.ai MCP Server."""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ....tools.registry import (
    Tool,
    ToolCategory,
    registry,
    ToolExecutionError,
)

router = APIRouter()


class ToolResponse(BaseModel):
    """Response model for tool endpoints."""

    tools: List[Tool]


class ToolExecuteRequest(BaseModel):
    """Request model for tool execution."""

    tool: str
    parameters: Dict[str, Any]
    action: Optional[str] = None


class ToolExecuteResponse(BaseModel):
    """Response model for tool execution."""

    status: str
    result: Any
    approval_required: Optional[bool] = None


@router.get("", response_model=ToolResponse)
async def list_tools():
    """List all available tools with their function signatures and parameters."""
    tools = registry.get_all_tools()
    return ToolResponse(tools=tools)


@router.get("/categories", response_model=List[ToolCategory])
async def list_tool_categories():
    """List all tool categories."""
    return registry.get_categories()


@router.get("/{category}", response_model=ToolResponse)
async def get_tools_by_category(category: ToolCategory):
    """Get tools for a specific category with their function signatures and parameters."""
    tools = registry.get_tools_by_category(category)
    if not tools:
        raise HTTPException(
            status_code=404, detail=f"No tools found for category: {category}"
        )
    return ToolResponse(tools=tools)


@router.get("/{category}/{tool_name}", response_model=Tool)
async def get_tool_by_path(category: ToolCategory, tool_name: str):
    """Execute a specific tool by category and name.

    Args:
        category: The category of the tool (e.g., KUBERNETES)
        tool_name: The name of the tool to execute

    Returns:
        Tool execution result

    Raises:
        HTTPException: If tool execution fails or tool not found
    """
    try:
        # Verify the tool exists in the specified category
        tools = registry.get_tools_by_category(category)
        tool_exists = any(t.name == tool_name for t in tools)

        if not tool_exists:
            raise HTTPException(
                status_code=404,
                detail=f"Tool '{tool_name}' not found in category '{category}'",
            )

        result = registry.get_tool(tool_name)
        return result
    except Exception as e:
        print(f"Error getting tool: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{category}/{tool_name}/execute", response_model=ToolExecuteResponse)
async def execute_tool_by_path(
    category: ToolCategory, tool_name: str, parameters: Dict[str, Any]
):
    """Execute a specific tool by category and name.

    Args:
        category: The category of the tool (e.g., KUBERNETES)
        tool_name: The name of the tool to execute
        parameters: The parameters to pass to the tool

    Returns:
        Tool execution result

    Raises:
        HTTPException: If tool execution fails or tool not found
    """
    try:
        # Verify the tool exists in the specified category
        tools = registry.get_tools_by_category(category)
        tool_exists = any(t.name == tool_name for t in tools)

        if not tool_exists:
            raise HTTPException(
                status_code=404,
                detail=f"Tool '{tool_name}' not found in category '{category}'",
            )

        result = await registry.execute_tool(tool_name, parameters)
        return ToolExecuteResponse(**result)
    except ToolExecutionError as e:
        print(f"Tool execution error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Internal server error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
