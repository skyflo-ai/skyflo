"""Argo Rollouts tools implementation for MCP server."""

import json
from typing import Optional

from pydantic import Field

from config.server import mcp
from utils.commands import run_command
from utils.models import ToolOutput


async def run_argo_command(command: str) -> ToolOutput:
    """Run an argo rollouts command and return its output."""
    cmd_parts = [part for part in command.split(" ") if part]
    return await run_command("kubectl", ["argo", "rollouts"] + cmd_parts)


@mcp.tool(title="List Argo Rollouts", tags=["argo"], annotations={"readOnlyHint": True})
async def argo_list_rollouts(
    namespace: Optional[str] = Field(default="default"),
    all_namespaces: Optional[bool] = Field(default=False),
) -> ToolOutput:
    """Get Argo Rollouts info."""
    # Use kubectl get directly since 'argo rollouts get rollouts' is not supported
    cmd_parts = ["get", "rollouts.argoproj.io", "-o", "wide"]
    if all_namespaces:
        cmd_parts.append("-A")
    elif namespace:
        cmd_parts.extend(["-n", namespace])
    return await run_command("kubectl", cmd_parts)


@mcp.tool(title="Promote Argo Rollout", tags=["argo"], annotations={"readOnlyHint": False})
async def argo_promote(
    name: str,
    namespace: Optional[str] = Field(default="default"),
    full: Optional[bool] = Field(
        default=False,
        description="Skip analysis, pauses, steps",
    ),
) -> ToolOutput:
    """Promote Argo Rollout to next step."""
    cmd = f"promote {name}"
    if namespace:
        cmd += f" -n {namespace}"
    if full:
        cmd += " --full"
    return await run_argo_command(cmd)


@mcp.tool(title="Pause Argo Rollout", tags=["argo"], annotations={"readOnlyHint": False})
async def argo_pause_rollout(
    name: str,
    namespace: Optional[str] = Field(default="default"),
) -> ToolOutput:
    """Pause Argo Rollout."""
    cmd = f"pause {name}"
    if namespace:
        cmd += f" -n {namespace}"
    return await run_argo_command(cmd)


@mcp.tool(title="Resume Argo Rollout", tags=["argo"], annotations={"readOnlyHint": False})
async def argo_resume_rollout(
    name: str,
    namespace: Optional[str] = Field(default="default"),
) -> ToolOutput:
    """Resume paused Argo Rollout."""
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
    name: str,
    namespace: Optional[str] = Field(default="default"),
) -> ToolOutput:
    """Abort Argo Rollout."""
    cmd = f"abort {name}"
    if namespace:
        cmd += f" -n {namespace}"
    return await run_argo_command(cmd)


@mcp.tool(title="Set Argo Rollout Image", tags=["argo"], annotations={"readOnlyHint": False})
async def argo_set_image(
    name: str,
    image: str,
    namespace: Optional[str] = Field(default="default"),
    container_name: Optional[str] = Field(
        default=None,
        description="Container to update. If omitted, image must be 'container=image' format.",
    ),
) -> ToolOutput:
    """Set Argo Rollout image."""
    if container_name:
        container_image = f"{container_name}={image}"
    elif "=" in image:
        container_image = image
    else:
        raise ValueError(
            "When container_name is omitted, image must be in 'container=image' format "
            "(e.g. 'myapp=nginx:1.25'). Alternatively, specify container_name explicitly."
        )

    cmd = f"set image {name} {container_image}"
    if namespace:
        cmd += f" -n {namespace}"
    return await run_argo_command(cmd)


@mcp.tool(title="Restart Argo Rollout", tags=["argo"], annotations={"readOnlyHint": False})
async def argo_rollout_restart(
    name: str,
    namespace: Optional[str] = Field(default="default"),
) -> ToolOutput:
    """Restart Argo Rollout."""
    cmd = f"restart {name}"
    if namespace:
        cmd += f" -n {namespace}"
    return await run_argo_command(cmd)


@mcp.tool(title="Get Argo Rollout Status", tags=["argo"], annotations={"readOnlyHint": True})
async def argo_status(
    name: str,
    namespace: Optional[str] = Field(default="default"),
    watch: Optional[bool] = Field(default=False, description="Watch status continuously"),
) -> ToolOutput:
    """Get Argo Rollout status."""
    cmd = f"status {name}"
    if namespace:
        cmd += f" -n {namespace}"
    if watch:
        cmd += " --watch"
    return await run_argo_command(cmd)


@mcp.tool(title="Get Argo Rollout History", tags=["argo"], annotations={"readOnlyHint": True})
async def argo_history(
    name: str,
    namespace: Optional[str] = Field(default="default"),
    revision: Optional[int] = Field(default=None, description="Omit for all revisions"),
) -> ToolOutput:
    """Get Argo Rollout history."""
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
    name: str,
    namespace: Optional[str] = Field(default="default"),
    to_revision: Optional[int] = Field(
        default=None,
        description="If omitted, rolls back to previous",
    ),
) -> ToolOutput:
    """Undo Argo Rollout to previous revision."""
    cmd = f"undo {name}"
    if namespace:
        cmd += f" -n {namespace}"
    if to_revision:
        cmd += f" --to-revision {to_revision}"
    return await run_argo_command(cmd)


@mcp.tool(title="Describe Argo Rollout", tags=["argo"], annotations={"readOnlyHint": True})
async def argo_describe(
    name: str,
    namespace: Optional[str] = Field(default="default"),
) -> ToolOutput:
    """Describe Argo Rollout."""
    # Use kubectl describe for rollouts
    cmd = f"describe rollouts.argoproj.io {name}"
    if namespace:
        cmd += f" -n {namespace}"
    return await run_command("kubectl", cmd.split())


@mcp.tool(title="List Argo Experiments", tags=["argo"], annotations={"readOnlyHint": True})
async def argo_list_experiments(
    rollout_name: Optional[str] = Field(
        default=None,
        description="If omitted, returns all",
    ),
    namespace: Optional[str] = Field(default=None),
    all_namespaces: Optional[bool] = Field(default=False),
) -> ToolOutput:
    """Get Argo Rollouts experiments."""
    if (
        isinstance(namespace, str)
        and namespace
        and isinstance(all_namespaces, bool)
        and all_namespaces
    ):
        raise ValueError("namespace and all_namespaces are mutually exclusive")
    if rollout_name:
        cmd_parts = ["get", "experiments.argoproj.io", "-o", "json"]
        if all_namespaces:
            cmd_parts.append("-A")
        elif namespace:
            cmd_parts.extend(["-n", namespace])

        result = await run_command("kubectl", cmd_parts)
        if result.get("error"):
            return result

        try:
            data = json.loads(result["output"])
            items = data.get("items", [])
            filtered_items = [
                item
                for item in items
                if any(
                    ref.get("kind") == "Rollout" and ref.get("name") == rollout_name
                    for ref in (item.get("metadata", {}).get("ownerReferences") or [])
                )
            ]
            if not filtered_items:
                return {
                    "output": f"No experiments found for rollout '{rollout_name}'",
                    "error": False,
                }
            return {
                "output": json.dumps({"items": filtered_items}, indent=2),
                "error": False,
            }
        except json.JSONDecodeError as e:
            return {"output": f"Failed to parse experiments JSON: {e}", "error": True}

    cmd_parts = ["get", "experiments.argoproj.io", "-o", "wide"]
    if all_namespaces:
        cmd_parts.append("-A")
    elif namespace:
        cmd_parts.extend(["-n", namespace])

    return await run_command("kubectl", cmd_parts)


@mcp.tool(title="List Argo Analysis Runs", tags=["argo"], annotations={"readOnlyHint": True})
async def argo_list_analysisruns(
    namespace: Optional[str] = Field(default=None),
    all_namespaces: Optional[bool] = Field(default=False),
) -> ToolOutput:
    """Get Argo Rollouts analysis runs."""
    if (
        isinstance(namespace, str)
        and namespace
        and isinstance(all_namespaces, bool)
        and all_namespaces
    ):
        raise ValueError("namespace and all_namespaces are mutually exclusive")
    cmd_parts = ["get", "analysisruns.argoproj.io", "-o", "wide"]
    if all_namespaces:
        cmd_parts.append("-A")
    elif namespace:
        cmd_parts.extend(["-n", namespace])
    return await run_command("kubectl", cmd_parts)
