"""Helm tools implementation for MCP server."""

import tempfile
import os
from typing import Optional
from pydantic import Field

from config.server import mcp
from utils.commands import run_command
from utils.types import ToolOutput


async def run_helm_command(command: str) -> ToolOutput:
    """Run a helm command and return its output."""
    cmd_parts = [part for part in command.split(" ") if part]
    return await run_command("helm", cmd_parts)


@mcp.tool(title="List Helm Releases", tags=["helm"], annotations={"readOnlyHint": True})
async def helm_list_releases(
    namespace: Optional[str] = Field(
        default=None, description="The namespace to list releases from"
    ),
    all_namespaces: Optional[bool] = Field(
        default=False, description="Whether to list releases from all namespaces"
    ),
) -> ToolOutput:
    """List Helm releases."""
    cmd = f"list {f'-n {namespace}' if namespace else ''} {'-A' if all_namespaces else ''}"
    return await run_helm_command(cmd)


@mcp.tool(
    title="Add Helm Repository", tags=["helm"], annotations={"readOnlyHint": False}
)
async def helm_repo_add(
    name: str = Field(description="The name of the Helm repository"),
    url: str = Field(description="The URL of the Helm repository"),
) -> ToolOutput:
    """Add a Helm repository."""
    return await run_helm_command(f"repo add {name} {url}")


@mcp.tool(
    title="Update Helm Repositories", tags=["helm"], annotations={"readOnlyHint": False}
)
async def helm_repo_update() -> ToolOutput:
    """Update Helm repositories."""
    return await run_helm_command("repo update")


@mcp.tool(
    title="Remove Helm Repository", tags=["helm"], annotations={"readOnlyHint": False}
)
async def helm_repo_remove(
    name: str = Field(description="The name of the Helm repository to remove"),
) -> ToolOutput:
    """Remove a Helm repository."""
    return await run_helm_command(f"repo remove {name}")


@mcp.tool(
    title="Install Helm Chart", tags=["helm"], annotations={"readOnlyHint": False}
)
async def helm_install(
    release_name: str = Field(description="The name of the Helm release"),
    chart: str = Field(description="The Helm chart to install"),
    namespace: Optional[str] = Field(
        default="default", description="The namespace to install the release in"
    ),
    create_namespace: Optional[bool] = Field(
        default=True, description="Whether to create the namespace if it doesn't exist"
    ),
    wait: Optional[bool] = Field(
        default=True, description="Whether to wait for the installation to complete"
    ),
) -> ToolOutput:
    """Install a Helm chart."""
    cmd = f"install {release_name} {chart}"
    if namespace:
        cmd += f" -n {namespace}"
    if create_namespace:
        cmd += " --create-namespace"
    if wait:
        cmd += " --wait"
    return await run_helm_command(cmd)


@mcp.tool(
    title="Install Helm Chart with Custom Values",
    tags=["helm"],
    annotations={"readOnlyHint": False},
)
async def helm_install_with_values(
    release_name: str = Field(description="The name of the Helm release"),
    chart: str = Field(description="The Helm chart to install"),
    values: str = Field(description="YAML values to pass to the chart"),
    namespace: Optional[str] = Field(
        default="default", description="The namespace to install the release in"
    ),
    create_namespace: Optional[bool] = Field(
        default=True, description="Whether to create the namespace if it doesn't exist"
    ),
    wait: Optional[bool] = Field(
        default=True, description="Whether to wait for the installation to complete"
    ),
) -> ToolOutput:
    """Install a Helm chart with custom values."""
    try:
        # Create a temporary values file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(values)
            values_file = f.name

        cmd = f"install {release_name} {chart} -f {values_file}"
        if namespace:
            cmd += f" -n {namespace}"
        if create_namespace:
            cmd += " --create-namespace"
        if wait:
            cmd += " --wait"

        result = await run_helm_command(cmd)

        # Clean up the temporary file
        os.unlink(values_file)
        return result
    except Exception as e:
        if "values_file" in locals():
            try:
                os.unlink(values_file)
            except:
                pass
        return {"output": f"Error installing Helm chart: {str(e)}", "error": True}


@mcp.tool(
    title="Upgrade Helm Release", tags=["helm"], annotations={"readOnlyHint": False}
)
async def helm_upgrade(
    release_name: str = Field(description="The name of the Helm release to upgrade"),
    chart: str = Field(description="The Helm chart to upgrade to"),
    namespace: Optional[str] = Field(
        default="default", description="The namespace of the release"
    ),
    install: Optional[bool] = Field(
        default=True, description="Whether to install if the release doesn't exist"
    ),
    wait: Optional[bool] = Field(
        default=True, description="Whether to wait for the upgrade to complete"
    ),
) -> ToolOutput:
    """Upgrade a Helm release."""
    cmd = f"upgrade {release_name} {chart}"
    if namespace:
        cmd += f" -n {namespace}"
    if install:
        cmd += " --install"
    if wait:
        cmd += " --wait"
    return await run_helm_command(cmd)


@mcp.tool(
    title="Uninstall Helm Release",
    tags=["helm"],
    annotations={"readOnlyHint": False, "destructiveHint": True},
)
async def helm_uninstall(
    release_name: str = Field(description="The name of the Helm release to uninstall"),
    namespace: Optional[str] = Field(
        default="default", description="The namespace of the release"
    ),
    keep_history: Optional[bool] = Field(
        default=False, description="Whether to keep the release history"
    ),
) -> ToolOutput:
    """Uninstall a Helm release."""
    cmd = f"uninstall {release_name}"
    if namespace:
        cmd += f" -n {namespace}"
    if keep_history:
        cmd += " --keep-history"
    return await run_helm_command(cmd)


@mcp.tool(
    title="Rollback Helm Release",
    tags=["helm"],
    annotations={"readOnlyHint": False, "destructiveHint": True},
)
async def helm_rollback(
    release_name: str = Field(description="The name of the Helm release to rollback"),
    revision: int = Field(description="The revision number to rollback to"),
    namespace: Optional[str] = Field(
        default="default", description="The namespace of the release"
    ),
    wait: Optional[bool] = Field(
        default=True, description="Whether to wait for the rollback to complete"
    ),
) -> ToolOutput:
    """Rollback a Helm release to a previous revision."""
    cmd = f"rollback {release_name} {revision}"
    if namespace:
        cmd += f" -n {namespace}"
    if wait:
        cmd += " --wait"
    return await run_helm_command(cmd)


@mcp.tool(
    title="Get Helm Release Status", tags=["helm"], annotations={"readOnlyHint": True}
)
async def helm_status(
    release_name: str = Field(description="The name of the Helm release"),
    namespace: Optional[str] = Field(
        default="default", description="The namespace of the release"
    ),
    output: Optional[str] = Field(
        default=None, description="Output format (json, yaml, table)"
    ),
) -> ToolOutput:
    """Get the status of a Helm release."""
    cmd = f"status {release_name}"
    if namespace:
        cmd += f" -n {namespace}"
    if output:
        cmd += f" -o {output}"
    return await run_helm_command(cmd)


@mcp.tool(
    title="Get Helm Release History", tags=["helm"], annotations={"readOnlyHint": True}
)
async def helm_history(
    release_name: str = Field(description="The name of the Helm release"),
    namespace: Optional[str] = Field(
        default="default", description="The namespace of the release"
    ),
    max_revisions: Optional[int] = Field(
        default=10, description="Maximum number of revisions to show"
    ),
) -> ToolOutput:
    """Get the revision history of a Helm release."""
    cmd = f"history {release_name}"
    if namespace:
        cmd += f" -n {namespace}"
    if max_revisions:
        cmd += f" --max {max_revisions}"
    return await run_helm_command(cmd)


@mcp.tool(
    title="Get Helm Release Values", tags=["helm"], annotations={"readOnlyHint": True}
)
async def helm_get_values(
    release_name: str = Field(description="The name of the Helm release"),
    namespace: Optional[str] = Field(
        default="default", description="The namespace of the release"
    ),
    output: Optional[str] = Field(
        default="yaml", description="Output format (yaml, json, table)"
    ),
) -> ToolOutput:
    """Get the values of a Helm release."""
    cmd = f"get values {release_name}"
    if namespace:
        cmd += f" -n {namespace}"
    if output:
        cmd += f" -o {output}"
    return await run_helm_command(cmd)


@mcp.tool(
    title="Get Helm Release Manifest", tags=["helm"], annotations={"readOnlyHint": True}
)
async def helm_get_manifest(
    release_name: str = Field(description="The name of the Helm release"),
    namespace: Optional[str] = Field(
        default="default", description="The namespace of the release"
    ),
) -> ToolOutput:
    """Get the manifest of a Helm release."""
    cmd = f"get manifest {release_name}"
    if namespace:
        cmd += f" -n {namespace}"
    return await run_helm_command(cmd)


@mcp.tool(
    title="Show Helm Chart Default Values",
    tags=["helm"],
    annotations={"readOnlyHint": True},
)
async def helm_show_values(
    chart: str = Field(description="The Helm chart to show values for"),
) -> ToolOutput:
    """Show the default values for a Helm chart."""
    return await run_helm_command(f"show values {chart}")


@mcp.tool(
    title="Search Helm Repositories", tags=["helm"], annotations={"readOnlyHint": True}
)
async def helm_search_repo(
    keyword: str = Field(description="The keyword to search for"),
    version: Optional[str] = Field(
        default=None, description="The chart version to search for"
    ),
    max_col_width: Optional[int] = Field(
        default=50, description="Maximum column width for output"
    ),
) -> ToolOutput:
    """Search Helm repositories for charts."""
    cmd = f"search repo {keyword}"
    if version:
        cmd += f" --version {version}"
    if max_col_width:
        cmd += f" --max-col-width {max_col_width}"
    return await run_helm_command(cmd)
