"""Argo Rollouts tools implementation for MCP server."""

import json
from typing import Optional
from pydantic import Field

from config.server import mcp
from utils.commands import run_command
from utils.types import ToolOutput


async def run_argo_command(command: str) -> ToolOutput:
    """Run an argo rollouts command and return its output."""
    cmd_parts = [part for part in command.split(" ") if part]
    return await run_command("kubectl", ["argo", "rollouts"] + cmd_parts)


@mcp.tool(title="List Argo Rollouts", tags=["argo"], annotations={"readOnlyHint": True})
async def argo_list_rollouts(
    namespace: Optional[str] = Field(
        default="default", description="The namespace to get rollouts from"
    ),
    all_namespaces: Optional[bool] = Field(
        default=False, description="Whether to get rollouts from all namespaces"
    ),
) -> ToolOutput:
    """Get Argo Rollouts information."""
    # Use kubectl get directly since 'argo rollouts get rollouts' is not supported
    cmd_parts = ["get", "rollouts.argoproj.io", "-o", "wide"]
    if all_namespaces:
        cmd_parts.append("-A")
    elif namespace:
        cmd_parts.extend(["-n", namespace])
    return await run_command("kubectl", cmd_parts)


@mcp.tool(
    title="Promote Argo Rollout", tags=["argo"], annotations={"readOnlyHint": False}
)
async def argo_promote(
    name: str = Field(description="The name of the rollout to promote"),
    namespace: Optional[str] = Field(
        default="default", description="The namespace of the rollout"
    ),
    full: Optional[bool] = Field(
        default=False,
        description="Whether to do a full promotion (skip analysis, pauses, and steps)",
    ),
) -> ToolOutput:
    """Promote an Argo Rollout to the next step."""
    cmd = f"promote {name}"
    if namespace:
        cmd += f" -n {namespace}"
    if full:
        cmd += " --full"
    return await run_argo_command(cmd)


@mcp.tool(
    title="Pause Argo Rollout", tags=["argo"], annotations={"readOnlyHint": False}
)
async def argo_pause_rollout(
    name: str = Field(description="The name of the rollout to pause"),
    namespace: Optional[str] = Field(
        default="default", description="The namespace of the rollout"
    ),
) -> ToolOutput:
    """Pause an Argo Rollout."""
    cmd = f"pause {name}"
    if namespace:
        cmd += f" -n {namespace}"
    return await run_argo_command(cmd)


@mcp.tool(
    title="Resume Argo Rollout", tags=["argo"], annotations={"readOnlyHint": False}
)
async def argo_resume_rollout(
    name: str = Field(description="The name of the rollout to resume"),
    namespace: Optional[str] = Field(
        default="default", description="The namespace of the rollout"
    ),
) -> ToolOutput:
    """Resume a paused Argo Rollout."""
    cmd = f"resume {name}"
    if namespace:
        cmd += f" -n {namespace}"
    return await run_argo_command(cmd)


@mcp.tool(
    title="Abort Argo Rollout",
    tags=["argo"],
    annotations={"readOnlyHint": False, "destructiveHint": True},
)
async def argo_abort_rollout(
    name: str = Field(description="The name of the rollout to abort"),
    namespace: Optional[str] = Field(
        default="default", description="The namespace of the rollout"
    ),
) -> ToolOutput:
    """Abort an Argo Rollout."""
    cmd = f"abort {name}"
    if namespace:
        cmd += f" -n {namespace}"
    return await run_argo_command(cmd)


@mcp.tool(
    title="Set Argo Rollout Image", tags=["argo"], annotations={"readOnlyHint": False}
)
async def argo_set_image(
    name: str = Field(description="The name of the rollout to update"),
    image: str = Field(description="The new container image"),
    namespace: Optional[str] = Field(
        default="default", description="The namespace of the rollout"
    ),
    container: Optional[str] = Field(
        default=None,
        description="The name of the container to update (if not specified, will use container=image format)",
    ),
) -> ToolOutput:
    """Set the image for an Argo Rollout."""
    if container:
        container_image = f"{container}={image}"
    else:
        # If no container specified, assume the image string is in container=image format
        container_image = image

    cmd = f"set image {name} {container_image}"
    if namespace:
        cmd += f" -n {namespace}"
    return await run_argo_command(cmd)


@mcp.tool(
    title="Restart Argo Rollout", tags=["argo"], annotations={"readOnlyHint": False}
)
async def argo_rollout_restart(
    name: str = Field(description="The name of the rollout to restart"),
    namespace: Optional[str] = Field(
        default="default", description="The namespace of the rollout"
    ),
) -> ToolOutput:
    """Restart an Argo Rollout."""
    cmd = f"restart {name}"
    if namespace:
        cmd += f" -n {namespace}"
    return await run_argo_command(cmd)


@mcp.tool(
    title="Get Argo Rollout Status", tags=["argo"], annotations={"readOnlyHint": True}
)
async def argo_status(
    name: str = Field(description="The name of the rollout to check status"),
    namespace: Optional[str] = Field(
        default="default", description="The namespace of the rollout"
    ),
    watch: Optional[bool] = Field(
        default=False, description="Whether to watch the status continuously"
    ),
) -> ToolOutput:
    """Get the status of an Argo Rollout."""
    cmd = f"status {name}"
    if namespace:
        cmd += f" -n {namespace}"
    if watch:
        cmd += " --watch"
    return await run_argo_command(cmd)


@mcp.tool(
    title="Get Argo Rollout History", tags=["argo"], annotations={"readOnlyHint": True}
)
async def argo_history(
    name: str = Field(description="The name of the rollout to get history for"),
    namespace: Optional[str] = Field(
        default="default", description="The namespace of the rollout"
    ),
    revision: Optional[int] = Field(
        default=None, description="Show details for a specific revision"
    ),
) -> ToolOutput:
    """Get the rollout history for an Argo Rollout."""
    cmd = f"history {name}"
    if namespace:
        cmd += f" -n {namespace}"
    if revision:
        cmd += f" --revision {revision}"
    return await run_argo_command(cmd)


@mcp.tool(
    title="Undo Argo Rollout",
    tags=["argo"],
    annotations={"readOnlyHint": False, "destructiveHint": True},
)
async def argo_undo(
    name: str = Field(description="The name of the rollout to undo"),
    namespace: Optional[str] = Field(
        default="default", description="The namespace of the rollout"
    ),
    to_revision: Optional[int] = Field(
        default=None,
        description="The revision to rollback to (if not specified, will rollback to previous revision)",
    ),
) -> ToolOutput:
    """Undo an Argo Rollout to a previous revision."""
    cmd = f"undo {name}"
    if namespace:
        cmd += f" -n {namespace}"
    if to_revision:
        cmd += f" --to-revision {to_revision}"
    return await run_argo_command(cmd)


@mcp.tool(
    title="Describe Argo Rollout", tags=["argo"], annotations={"readOnlyHint": True}
)
async def argo_describe(
    name: str = Field(description="The name of the rollout to describe"),
    namespace: Optional[str] = Field(
        default="default", description="The namespace of the rollout"
    ),
) -> ToolOutput:
    """Describe an Argo Rollout in detail."""
    # Use kubectl describe for rollouts
    cmd = f"describe rollouts.argoproj.io {name}"
    if namespace:
        cmd += f" -n {namespace}"
    return await run_command("kubectl", cmd.split())


@mcp.tool(
    title="List Argo Experiments", tags=["argo"], annotations={"readOnlyHint": True}
)
async def argo_list_experiments(
    rollout_name: Optional[str] = Field(
        default=None,
        description="The name of the rollout to filter experiments by. Experiments are filtered by checking if their name starts with the rollout name (Argo Rollouts naming convention: {rollout-name}-{hash}-{revision}-{step}). If not specified, returns all experiments.",
    ),
    namespace: Optional[str] = Field(
        default="default", description="The namespace to get experiments from"
    ),
    all_namespaces: Optional[bool] = Field(
        default=False, description="Whether to get experiments from all namespaces"
    ),
) -> ToolOutput:
    """Get Argo Rollouts experiments, optionally filtered by rollout name.
    
    When rollout_name is provided, experiments are filtered by checking if their
    name starts with the rollout name, following Argo Rollouts' naming convention
    where experiment names are: {rollout-name}-{podHash}-{revision}-{stepIndex}.
    """
    # Get experiments in JSON format for filtering, or wide format for display
    if rollout_name:
        # Use JSON output to filter by experiment name prefix (rollout name)
        cmd_parts = ["get", "experiments.argoproj.io", "-o", "json"]
    else:
        cmd_parts = ["get", "experiments.argoproj.io", "-o", "wide"]
    
    if all_namespaces:
        cmd_parts.append("-A")
    elif namespace:
        cmd_parts.extend(["-n", namespace])

    result = await run_command("kubectl", cmd_parts)
    
    # If filtering by rollout name, parse JSON and filter experiments
    if rollout_name and result.get("output") and not result.get("error"):
        try:
            data = json.loads(result["output"])
            items = data.get("items", [])
            # Filter experiments whose name starts with the rollout name
            filtered = [
                exp for exp in items 
                if exp.get("metadata", {}).get("name", "").startswith(f"{rollout_name}-")
            ]
            if filtered:
                # Format output as a readable list
                output_lines = ["NAME\t\tSTATUS\t\tAGE"]
                for exp in filtered:
                    name = exp.get("metadata", {}).get("name", "")
                    status = exp.get("status", {}).get("phase", "Unknown")
                    created = exp.get("metadata", {}).get("creationTimestamp", "")
                    output_lines.append(f"{name}\t{status}\t{created}")
                result["output"] = "\n".join(output_lines)
            else:
                result["output"] = f"No experiments found for rollout '{rollout_name}'"
        except json.JSONDecodeError:
            # If JSON parsing fails, return original output
            pass
    
    return result


@mcp.tool(
    title="List Argo Analysis Runs", tags=["argo"], annotations={"readOnlyHint": True}
)
async def argo_list_analysisruns(
    namespace: Optional[str] = Field(
        default="default", description="The namespace to get analysis runs from"
    ),
    all_namespaces: Optional[bool] = Field(
        default=False, description="Whether to get analysis runs from all namespaces"
    ),
) -> ToolOutput:
    """Get Argo Rollouts analysis runs."""
    cmd_parts = ["get", "analysisruns.argoproj.io", "-o", "wide"]
    if all_namespaces:
        cmd_parts.append("-A")
    elif namespace:
        cmd_parts.extend(["-n", namespace])
    return await run_command("kubectl", cmd_parts)
