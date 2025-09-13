"""Kubernetes tools implementation for MCP server."""

import asyncio
from typing import Optional
from pydantic import Field

from config.server import mcp
from utils.commands import run_command
from utils.types import ToolOutput


async def run_kubectl_command(command: str, stdin: Optional[str] = None) -> ToolOutput:
    """Run a kubectl command and return its output."""
    cmd_parts = [part for part in command.split(" ") if part]
    return await run_command("kubectl", cmd_parts, stdin=stdin)


@mcp.tool(
    title="Get Kubernetes Pod Logs", tags=["k8s"], annotations={"readOnlyHint": True}
)
async def k8s_logs(
    pod_name: str = Field(description="The name of the pod to get logs from"),
    namespace: Optional[str] = Field(
        default="default", description="The namespace of the pod to get logs from"
    ),
    num_lines: Optional[int] = Field(
        default=50, description="The number of lines to get from the logs"
    ),
) -> ToolOutput:
    """Get logs from a Kubernetes pod."""
    return await run_kubectl_command(
        f"logs {pod_name} {f'-n {namespace}' if namespace else ''} --tail {num_lines}"
    )


@mcp.tool(
    title="Get Kubernetes Resources", tags=["k8s"], annotations={"readOnlyHint": True}
)
async def k8s_get(
    resource_type: str = Field(
        description="The type of resource to get information about (deployment, service, pod, node, ...)"
    ),
    name: Optional[str] = Field(
        default=None,
        description="The name of the resource to get information about. If not provided, all resources of the given type will be returned",
    ),
    all_namespaces: Optional[bool] = Field(
        default=False, description="Whether to get resources from all namespaces"
    ),
    namespace: Optional[str] = Field(
        default=None, description="The namespace to get resources from"
    ),
    output: Optional[str] = Field(
        default=None, description="Output format (wide, yaml, json)"
    ),
) -> ToolOutput:
    """Get information about Kubernetes resources."""
    if not resource_type:
        raise ValueError("resource_type is required")

    if name and all_namespaces:
        all_namespaces = False

    return await run_kubectl_command(
        f"get {resource_type} {name if name else ''} {'-n ' + namespace + ' ' if namespace else ''}{'-o ' + output if output else ''} {'-A' if all_namespaces else ''}"
    )


@mcp.tool(
    title="Describe Kubernetes Resource",
    tags=["k8s"],
    annotations={"readOnlyHint": True},
)
async def k8s_describe(
    name: str = Field(description="The name of the resource to describe"),
    resource_type: str = Field(
        description="The type of resource to describe (deployment, service, pod, node, ...)"
    ),
    namespace: Optional[str] = Field(
        default="default", description="The namespace of the resource"
    ),
) -> ToolOutput:
    """Describe a Kubernetes resource in detail."""
    return await run_kubectl_command(
        f"describe {resource_type} {name} {f'-n {namespace}' if namespace else ''}"
    )


@mcp.tool(
    title="Apply Kubernetes Manifest", tags=["k8s"], annotations={"readOnlyHint": False}
)
async def k8s_apply(
    content: str = Field(description="The YAML manifest content to apply"),
    namespace: Optional[str] = Field(
        default=None, description="The namespace to apply the manifest to"
    ),
) -> ToolOutput:
    """Apply a Kubernetes manifest from provided YAML content."""
    return await run_kubectl_command(
        f"apply -f - {f'-n {namespace}' if namespace else ''}", stdin=content
    )


@mcp.tool(
    title="Patch Kubernetes Resource", tags=["k8s"], annotations={"readOnlyHint": False}
)
async def k8s_patch(
    name: str = Field(description="The name of the resource to patch"),
    resource_type: str = Field(description="The type of resource to patch"),
    patch: str = Field(description="The patch to apply (JSON or YAML)"),
    namespace: Optional[str] = Field(
        default="default", description="The namespace of the resource"
    ),
    patch_type: Optional[str] = Field(
        default="strategic", description="The type of patch (strategic, merge, json)"
    ),
) -> ToolOutput:
    """Patch a Kubernetes resource."""
    return await run_kubectl_command(
        f"patch {resource_type} {name} {f'-n {namespace}' if namespace else ''} --patch {patch} --type={patch_type}"
    )


@mcp.tool(
    title="Update Kubernetes Container Images",
    tags=["k8s"],
    annotations={"readOnlyHint": False},
)
async def k8s_set_image(
    resource_name: str = Field(description="The name of the resource to update"),
    resource_type: str = Field(description="The type of resource to update"),
    container_images: str = Field(
        description="Container image updates in format 'container1=image1,container2=image2'"
    ),
    namespace: Optional[str] = Field(
        default=None, description="The namespace of the resource"
    ),
) -> ToolOutput:
    """Update container images for a Kubernetes resource."""
    return await run_kubectl_command(
        f"set image {resource_type}/{resource_name} {container_images} {f'-n {namespace}' if namespace else ''}"
    )


@mcp.tool(
    title="Restart Kubernetes Deployment",
    tags=["k8s"],
    annotations={"readOnlyHint": False},
)
async def k8s_rollout_restart(
    name: str = Field(description="The name of the deployment to restart"),
    namespace: Optional[str] = Field(
        default="default", description="The namespace of the deployment"
    ),
) -> ToolOutput:
    """Restart a Kubernetes deployment."""
    return await run_kubectl_command(
        f"rollout restart deployment/{name} {f'-n {namespace}' if namespace else ''}"
    )


@mcp.tool(
    title="Scale Kubernetes Resource", tags=["k8s"], annotations={"readOnlyHint": False}
)
async def k8s_scale(
    name: str = Field(description="The name of the resource to scale"),
    resource_type: str = Field(description="The type of resource to scale"),
    replicas: int = Field(description="The number of replicas to scale to"),
    namespace: Optional[str] = Field(
        default="default", description="The namespace of the resource"
    ),
) -> ToolOutput:
    """Scale a Kubernetes resource."""
    return await run_kubectl_command(
        f"scale {resource_type}/{name} --replicas={replicas} {f'-n {namespace} ' if namespace else ''}"
    )


@mcp.tool(
    title="Delete Kubernetes Resource",
    tags=["k8s"],
    annotations={"readOnlyHint": False, "destructiveHint": True},
)
async def k8s_delete(
    name: str = Field(description="The name of the resource to delete"),
    resource_type: str = Field(description="The type of resource to delete"),
    namespace: Optional[str] = Field(
        default="default", description="The namespace of the resource"
    ),
) -> ToolOutput:
    """Delete a Kubernetes resource."""
    return await run_kubectl_command(
        f"delete {resource_type} {name} {f'-n {namespace}' if namespace else ''}"
    )


@mcp.tool(
    title="Wait for Specified Duration",
    tags=["k8s"],
    annotations={"readOnlyHint": True},
)
async def wait_for_x_seconds(
    seconds: int = Field(description="The number of seconds to wait"),
) -> ToolOutput:
    """Wait for a specified number of seconds."""
    await asyncio.sleep(seconds)
    return {"output": f"Waited for {seconds} seconds", "error": False}


@mcp.tool(
    title="Check Kubernetes Rollout Status",
    tags=["k8s"],
    annotations={"readOnlyHint": True},
)
async def k8s_rollout_status(
    name: str = Field(description="The name of the deployment to check rollout status"),
    namespace: Optional[str] = Field(
        default="default", description="The namespace of the deployment"
    ),
) -> ToolOutput:
    """Check the rollout status of a Kubernetes deployment."""
    return await run_kubectl_command(
        f"rollout status deployment/{name} {f'-n {namespace}' if namespace else ''}"
    )


@mcp.tool(
    title="Get Kubernetes Cluster Information",
    tags=["k8s"],
    annotations={"readOnlyHint": True},
)
async def k8s_cluster_info() -> ToolOutput:
    """Get information about the Kubernetes cluster."""
    return await run_kubectl_command("cluster-info")


@mcp.tool(
    title="Cordon Kubernetes Node", tags=["k8s"], annotations={"readOnlyHint": False}
)
async def k8s_cordon(
    node_name: str = Field(description="The name of the node to cordon"),
) -> ToolOutput:
    """Cordon a Kubernetes node to prevent new pods from being scheduled."""
    return await run_kubectl_command(f"cordon {node_name}")


@mcp.tool(
    title="Uncordon Kubernetes Node", tags=["k8s"], annotations={"readOnlyHint": False}
)
async def k8s_uncordon(
    node_name: str = Field(description="The name of the node to uncordon"),
) -> ToolOutput:
    """Uncordon a Kubernetes node to allow new pods to be scheduled."""
    return await run_kubectl_command(f"uncordon {node_name}")


@mcp.tool(
    title="Drain Kubernetes Node",
    tags=["k8s"],
    annotations={"readOnlyHint": False, "destructiveHint": True},
)
async def k8s_drain(
    node_name: str = Field(description="The name of the node to drain"),
    ignore_daemonsets: Optional[bool] = Field(
        default=True, description="Whether to ignore DaemonSets when draining"
    ),
    delete_emptydir_data: Optional[bool] = Field(
        default=False, description="Whether to delete emptyDir data when draining"
    ),
) -> ToolOutput:
    """Drain a Kubernetes node by evicting all pods."""
    cmd = f"drain {node_name}"
    if ignore_daemonsets:
        cmd += " --ignore-daemonsets"
    if delete_emptydir_data:
        cmd += " --delete-emptydir-data"
    return await run_kubectl_command(cmd)


@mcp.tool(title="Run Kubernetes Pod", tags=["k8s"], annotations={"readOnlyHint": False})
async def k8s_run_pod(
    name: str = Field(description="The name of the pod to run"),
    image: str = Field(description="The container image to run"),
    namespace: Optional[str] = Field(
        default="default", description="The namespace to run the pod in"
    ),
    command: Optional[str] = Field(
        default=None, description="The command to run in the pod"
    ),
) -> ToolOutput:
    """Run a temporary pod in the Kubernetes cluster."""
    cmd = f"run {name} --image={image}"
    if namespace:
        cmd += f" -n {namespace}"
    if command:
        cmd += f" --command -- {command}"
    return await run_kubectl_command(cmd)


@mcp.tool(
    title="Execute Command in Kubernetes Pod",
    tags=["k8s"],
    annotations={"readOnlyHint": False},
)
async def k8s_exec(
    pod_name: str = Field(description="The name of the pod to execute command in"),
    command: str = Field(description="The command to execute inside the pod"),
    namespace: Optional[str] = Field(
        default="default", description="The namespace of the pod"
    ),
    container: Optional[str] = Field(
        default=None, description="The container name (if pod has multiple containers)"
    ),
) -> ToolOutput:
    """Execute a command inside a Kubernetes pod."""
    cmd = f"exec {pod_name}"
    if namespace:
        cmd += f" -n {namespace}"
    if container:
        cmd += f" -c {container}"
    cmd += f" -- {command}"
    return await run_kubectl_command(cmd)


@mcp.tool(
    title="Port Forward to Kubernetes Resource",
    tags=["k8s"],
    annotations={"readOnlyHint": False},
)
async def k8s_port_forward(
    resource_name: str = Field(
        description="The name of the resource to port forward to"
    ),
    ports: str = Field(description="Port mapping in format 'local_port:remote_port'"),
    namespace: Optional[str] = Field(
        default="default", description="The namespace of the resource"
    ),
    resource_type: Optional[str] = Field(
        default="pod", description="The type of resource (pod, service, deployment)"
    ),
) -> ToolOutput:
    """Port forward to a Kubernetes resource."""
    resource_spec = (
        f"{resource_type}/{resource_name}" if resource_type != "pod" else resource_name
    )
    return await run_kubectl_command(
        f"port-forward {resource_spec} {ports} {f'-n {namespace}' if namespace else ''}"
    )
