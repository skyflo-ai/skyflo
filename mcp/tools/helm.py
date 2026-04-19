"""Helm tools implementation for MCP server."""

import os
import tempfile
from typing import Optional

from pydantic import Field

from config.server import mcp
from utils.commands import run_command
from utils.models import ToolOutput


async def run_helm_command(command: str) -> ToolOutput:
    """Run a helm command and return its output."""
    cmd_parts = [part for part in command.split(" ") if part]
    return await run_command("helm", cmd_parts)


@mcp.tool(title="List Helm Releases", tags=["helm"], annotations={"readOnlyHint": True})
async def helm_list_releases(
    namespace: Optional[str] = Field(default=None),
    all_namespaces: Optional[bool] = Field(default=False),
) -> ToolOutput:
    """List Helm releases."""
    if (
        isinstance(namespace, str)
        and namespace
        and isinstance(all_namespaces, bool)
        and all_namespaces
    ):
        raise ValueError("namespace and all_namespaces are mutually exclusive")
    cmd = f"list {f'-n {namespace}' if namespace else ''} {'-A' if all_namespaces else ''}"
    return await run_helm_command(cmd)


@mcp.tool(title="Add Helm Repository", tags=["helm"], annotations={"readOnlyHint": False})
async def helm_repo_add(
    name: str,
    url: str,
) -> ToolOutput:
    """Add Helm repository."""
    return await run_helm_command(f"repo add {name} {url}")


@mcp.tool(title="Update Helm Repositories", tags=["helm"], annotations={"readOnlyHint": False})
async def helm_repo_update() -> ToolOutput:
    """Update Helm repositories."""
    return await run_helm_command("repo update")


@mcp.tool(title="Remove Helm Repository", tags=["helm"], annotations={"readOnlyHint": False})
async def helm_repo_remove(
    name: str,
) -> ToolOutput:
    """Remove Helm repository."""
    return await run_helm_command(f"repo remove {name}")


@mcp.tool(title="Install Helm Chart", tags=["helm"], annotations={"readOnlyHint": False})
async def helm_install(
    release_name: str,
    chart: str,
    namespace: Optional[str] = Field(default="default"),
    create_namespace: Optional[bool] = Field(
        default=True, description="Create namespace if missing"
    ),
    wait: Optional[bool] = Field(default=True, description="Block until resources are ready"),
) -> ToolOutput:
    """Install Helm chart."""
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
    release_name: str,
    chart: str,
    values: str = Field(description="YAML values content"),
    namespace: Optional[str] = Field(default="default"),
    create_namespace: Optional[bool] = Field(
        default=True, description="Create namespace if missing"
    ),
    wait: Optional[bool] = Field(default=True, description="Block until resources are ready"),
) -> ToolOutput:
    """Install Helm chart with custom values."""
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
            except OSError:
                pass
        return {"output": f"Error installing Helm chart: {str(e)}", "error": True}


@mcp.tool(title="Upgrade Helm Release", tags=["helm"], annotations={"readOnlyHint": False})
async def helm_upgrade(
    release_name: str,
    chart: str,
    namespace: Optional[str] = Field(default=None),
    install: Optional[bool] = Field(default=True, description="Install if release does not exist"),
    wait: Optional[bool] = Field(default=True, description="Block until resources are ready"),
) -> ToolOutput:
    """Upgrade Helm release."""
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
    release_name: str,
    namespace: Optional[str] = Field(default=None),
    keep_history: Optional[bool] = Field(default=False, description="Retain release history"),
) -> ToolOutput:
    """Uninstall Helm release."""
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
    release_name: str,
    revision: int,
    namespace: Optional[str] = Field(default=None),
    wait: Optional[bool] = Field(default=True, description="Block until rollback completes"),
) -> ToolOutput:
    """Rollback Helm release to previous revision."""
    cmd = f"rollback {release_name} {revision}"
    if namespace:
        cmd += f" -n {namespace}"
    if wait:
        cmd += " --wait"
    return await run_helm_command(cmd)


@mcp.tool(title="Get Helm Release Status", tags=["helm"], annotations={"readOnlyHint": True})
async def helm_status(
    release_name: str,
    namespace: Optional[str] = Field(default=None),
    output: Optional[str] = Field(default=None, description="'json', 'yaml', 'table'"),
) -> ToolOutput:
    """Get Helm release status."""
    cmd = f"status {release_name}"
    if namespace:
        cmd += f" -n {namespace}"
    if output:
        cmd += f" -o {output}"
    return await run_helm_command(cmd)


@mcp.tool(title="Get Helm Release History", tags=["helm"], annotations={"readOnlyHint": True})
async def helm_history(
    release_name: str,
    namespace: Optional[str] = Field(default=None),
    max_revisions: Optional[int] = Field(default=10, description="Max revisions to return"),
) -> ToolOutput:
    """Get Helm release revision history."""
    cmd = f"history {release_name}"
    if namespace:
        cmd += f" -n {namespace}"
    if max_revisions:
        cmd += f" --max {max_revisions}"
    return await run_helm_command(cmd)


@mcp.tool(title="Get Helm Release Values", tags=["helm"], annotations={"readOnlyHint": True})
async def helm_get_values(
    release_name: str,
    namespace: Optional[str] = Field(default=None),
    output: Optional[str] = Field(default="yaml", description="'yaml', 'json', 'table'"),
) -> ToolOutput:
    """Get Helm release values."""
    cmd = f"get values {release_name}"
    if namespace:
        cmd += f" -n {namespace}"
    if output:
        cmd += f" -o {output}"
    return await run_helm_command(cmd)


@mcp.tool(title="Get Helm Release Manifest", tags=["helm"], annotations={"readOnlyHint": True})
async def helm_get_manifest(
    release_name: str,
    namespace: Optional[str] = Field(default=None),
) -> ToolOutput:
    """Get Helm release manifest."""
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
    chart: str,
) -> ToolOutput:
    """Show Helm chart default values."""
    return await run_helm_command(f"show values {chart}")


@mcp.tool(title="Search Helm Repositories", tags=["helm"], annotations={"readOnlyHint": True})
async def helm_search_repo(
    keyword: str,
    version: Optional[str] = Field(default=None),
    max_col_width: Optional[int] = Field(default=50),
) -> ToolOutput:
    """Search Helm repos charts."""
    cmd = f"search repo {keyword}"
    if version:
        cmd += f" --version {version}"
    if max_col_width:
        cmd += f" --max-col-width {max_col_width}"
    return await run_helm_command(cmd)


@mcp.tool(title="Render Helm Template", tags=["helm"], annotations={"readOnlyHint": True})
async def helm_template(
    release_name: str,
    chart: str,
    namespace: Optional[str] = Field(default=None),
    values: Optional[str] = Field(default=None, description="YAML values content"),
    include_crds: Optional[bool] = Field(default=False, description="Include CRDs in output"),
) -> ToolOutput:
    """Render Helm chart templates, preview manifests."""
    cmd = f"template {release_name} {chart}"

    if namespace:
        cmd += f" -n {namespace}"

    if include_crds:
        cmd += " --include-crds"

    if values:
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                f.write(values)
                values_file = f.name

            cmd += f" -f {values_file}"
            result = await run_helm_command(cmd)

            os.unlink(values_file)
            return result
        except Exception as e:
            if "values_file" in locals():
                try:
                    os.unlink(values_file)
                except OSError:
                    pass
            return {"output": f"Error rendering Helm template: {str(e)}", "error": True}
    else:
        return await run_helm_command(cmd)
