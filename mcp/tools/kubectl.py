"""Kubernetes tools implementation for MCP server."""

import asyncio
import shlex
from typing import Annotated, Optional

from pydantic import Field

from config.server import mcp
from utils.commands import run_command
from utils.models import ToolOutput

_VALID_OUTPUT_FORMATS: frozenset[str] = frozenset({"wide", "yaml", "json", "name"})
_VALID_PATCH_TYPES: frozenset[str] = frozenset({"strategic", "merge", "json"})


def _normalize_enum_arg(
    value: object,
    *,
    param_name: str,
    allowed_values: frozenset[str],
    default: Optional[str] = None,
) -> Optional[str]:
    allowed_sorted = sorted(allowed_values)

    if value is None:
        return default

    if not isinstance(value, str):
        raise ValueError(
            f"Invalid {param_name} {value!r}. Must be one of: {', '.join(allowed_sorted)}"
        )

    normalized = value.strip().lower()

    if normalized == "":
        raise ValueError(
            f"Invalid {param_name} '{value}'. Must be one of: {', '.join(allowed_sorted)}"
        )

    if normalized not in allowed_values:
        raise ValueError(
            f"Invalid {param_name} '{value.strip()}'. Must be one of: {', '.join(allowed_sorted)}"
        )

    return normalized


async def run_kubectl_command(command: str, stdin: Optional[str] = None) -> ToolOutput:
    """Run a kubectl command and return its output."""
    cmd_parts = [part for part in command.split(" ") if part]
    return await run_command("kubectl", cmd_parts, stdin=stdin)


@mcp.tool(title="Get Kubernetes Pod Logs", tags=["k8s"], annotations={"readOnlyHint": True})
async def k8s_logs(
    pod_name: str,
    namespace: Optional[str] = Field(default="default"),
    num_lines: Optional[int] = Field(default=50, description="Tail lines to return"),
    container_name: Optional[str] = Field(
        default=None,
        description="Container to read from. Required for multi-container pods.",
    ),
    since: Optional[str] = Field(
        default=None,
        description="Relative duration window: 5s, 2m, 3h",
    ),
    previous: Optional[bool] = Field(
        default=False,
        description="Read logs from the previous container instance",
    ),
) -> ToolOutput:
    """Get Kubernetes pod logs."""
    cmd_parts = ["logs", pod_name]

    if namespace:
        cmd_parts.extend(["-n", namespace])

    if container_name:
        cmd_parts.extend(["-c", container_name])

    if since:
        cmd_parts.extend(["--since", since])

    if previous:
        cmd_parts.append("--previous")

    if num_lines is not None:
        cmd_parts.extend(["--tail", str(num_lines)])

    return await run_command("kubectl", cmd_parts)


@mcp.tool(title="Get Kubernetes Resources", tags=["k8s"], annotations={"readOnlyHint": True})
async def k8s_get(
    resource_type: str = Field(description="e.g. deployment, service, pod, node"),
    name: Optional[str] = Field(
        default=None,
        description="If omitted, returns all",
    ),
    all_namespaces: Optional[bool] = Field(default=False),
    namespace: Optional[str] = Field(default=None),
    output: Annotated[
        Optional[str],
        Field(description="'wide', 'yaml', 'json', 'name'"),
    ] = None,
    label_selector: Optional[str] = Field(
        default=None,
        description="e.g. 'app=nginx'",
    ),
) -> ToolOutput:
    """Get Kubernetes resource info."""
    if not resource_type:
        raise ValueError("resource_type is required")

    if (
        isinstance(namespace, str)
        and namespace
        and isinstance(all_namespaces, bool)
        and all_namespaces
    ):
        raise ValueError("namespace and all_namespaces are mutually exclusive")

    if isinstance(name, str) and name and all_namespaces:
        all_namespaces = False

    output_normalized = _normalize_enum_arg(
        output,
        param_name="output format",
        allowed_values=_VALID_OUTPUT_FORMATS,
        default=None,
    )

    args = ["get", resource_type]
    if isinstance(name, str) and name:
        args.append(name)
    if isinstance(namespace, str) and namespace:
        args.extend(["-n", namespace])
    if output_normalized is not None:
        args.extend(["-o", output_normalized])
    if isinstance(all_namespaces, bool) and all_namespaces:
        args.append("-A")
    if isinstance(label_selector, str) and label_selector:
        args.extend(["-l", label_selector])
    return await run_command("kubectl", args)


@mcp.tool(
    title="Describe Kubernetes Resource",
    tags=["k8s"],
    annotations={"readOnlyHint": True},
)
async def k8s_describe(
    name: str,
    resource_type: str = Field(description="e.g. deployment, service, pod, node"),
    namespace: Optional[str] = Field(default="default"),
) -> ToolOutput:
    """Describe Kubernetes resource."""
    return await run_kubectl_command(
        f"describe {resource_type} {name} {f'-n {namespace}' if namespace else ''}"
    )


@mcp.tool(title="Apply Kubernetes Manifest", tags=["k8s"], annotations={"readOnlyHint": False})
async def k8s_apply(
    content: str = Field(description="YAML manifest"),
    namespace: Optional[str] = Field(default=None),
) -> ToolOutput:
    """Apply Kubernetes YAML manifest."""
    return await run_kubectl_command(
        f"apply -f - {f'-n {namespace}' if namespace else ''}", stdin=content
    )


@mcp.tool(title="Patch Kubernetes Resource", tags=["k8s"], annotations={"readOnlyHint": False})
async def k8s_patch(
    name: str,
    resource_type: str,
    patch: str = Field(description="JSON or YAML"),
    namespace: Optional[str] = Field(default="default"),
    patch_type: Annotated[
        Optional[str],
        Field(description="'strategic', 'merge', 'json'"),
    ] = None,
) -> ToolOutput:
    """Patch Kubernetes resource."""

    patch_type_normalized = _normalize_enum_arg(
        patch_type,
        param_name="patch_type",
        allowed_values=_VALID_PATCH_TYPES,
        default="strategic",
    )

    args = ["patch", resource_type, name]
    if isinstance(namespace, str) and namespace:
        args.extend(["-n", namespace])
    args.append("--patch")
    args.append(patch)
    args.append(f"--type={patch_type_normalized}")
    return await run_command("kubectl", args)


@mcp.tool(
    title="Update Kubernetes Container Images",
    tags=["k8s"],
    annotations={"readOnlyHint": False},
)
async def k8s_set_image(
    resource_name: str,
    resource_type: str,
    container_images: str = Field(description="Format: 'container1=image1,container2=image2'"),
    namespace: Optional[str] = Field(default=None),
) -> ToolOutput:
    """Update Kubernetes resource container images."""
    return await run_kubectl_command(
        f"set image {resource_type}/{resource_name} {container_images} {f'-n {namespace}' if namespace else ''}"
    )


@mcp.tool(
    title="Restart Kubernetes Deployment",
    tags=["k8s"],
    annotations={"readOnlyHint": False},
)
async def k8s_rollout_restart(
    name: str,
    namespace: Optional[str] = Field(default="default"),
) -> ToolOutput:
    """Restart Kubernetes deployment."""
    return await run_kubectl_command(
        f"rollout restart deployment/{name} {f'-n {namespace}' if namespace else ''}"
    )


@mcp.tool(title="Scale Kubernetes Resource", tags=["k8s"], annotations={"readOnlyHint": False})
async def k8s_scale(
    name: str,
    resource_type: str,
    replicas: int = Field(description="Target replica count"),
    namespace: Optional[str] = Field(default="default"),
) -> ToolOutput:
    """Scale Kubernetes resource."""
    return await run_kubectl_command(
        f"scale {resource_type}/{name} --replicas={replicas} {f'-n {namespace} ' if namespace else ''}"
    )


@mcp.tool(
    title="Delete Kubernetes Resource",
    tags=["k8s"],
    annotations={"readOnlyHint": False, "destructiveHint": True},
)
async def k8s_delete(
    name: str,
    resource_type: str,
    namespace: Optional[str] = Field(default="default"),
) -> ToolOutput:
    """Delete Kubernetes resource."""
    return await run_kubectl_command(
        f"delete {resource_type} {name} {f'-n {namespace}' if namespace else ''}"
    )


MAX_SLEEP_SECONDS = 300


@mcp.tool(
    title="Wait for Specified Duration",
    tags=["k8s"],
    annotations={"readOnlyHint": True},
)
async def wait_for_x_seconds(
    seconds: int = Field(description=f"Seconds to wait (max {MAX_SLEEP_SECONDS})"),
) -> ToolOutput:
    """Wait specified seconds."""
    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        return {"output": "Invalid seconds value: must be an integer", "error": True}

    if seconds < 0:
        return {"output": "Invalid seconds value: must be non-negative", "error": True}

    if seconds > MAX_SLEEP_SECONDS:
        return {
            "output": f"Requested {seconds}s exceeds maximum allowed ({MAX_SLEEP_SECONDS}s)",
            "error": True,
        }

    await asyncio.sleep(seconds)
    return {"output": f"Waited for {seconds} seconds", "error": False}


@mcp.tool(
    title="Check Kubernetes Rollout Status",
    tags=["k8s"],
    annotations={"readOnlyHint": True},
)
async def k8s_rollout_status(
    name: str,
    namespace: Optional[str] = Field(default="default"),
) -> ToolOutput:
    """Check Kubernetes deployment rollout status."""
    return await run_kubectl_command(
        f"rollout status deployment/{name} {f'-n {namespace}' if namespace else ''}"
    )


@mcp.tool(
    title="Rollback Kubernetes Resource",
    tags=["k8s"],
    annotations={"readOnlyHint": False},
)
async def k8s_rollout_undo(
    name: str,
    resource_type: str = Field(description="'deployment', 'daemonset', or 'statefulset'"),
    namespace: Optional[str] = Field(default="default"),
    to_revision: Optional[int] = Field(
        default=None,
        description="If omitted, rolls back to previous",
    ),
) -> ToolOutput:
    """Rollback Kubernetes resource to previous or specific revision."""
    valid_resource_types = ["deployment", "daemonset", "statefulset"]
    if resource_type.lower() not in valid_resource_types:
        raise ValueError(
            f"Invalid resource_type '{resource_type}'. Must be one of: {', '.join(valid_resource_types)}"
        )

    cmd = f"rollout undo {resource_type.lower()}/{name}"

    if namespace:
        cmd += f" -n {namespace}"

    if to_revision is not None:
        cmd += f" --to-revision={to_revision}"

    return await run_kubectl_command(cmd)


@mcp.tool(
    title="View Kubernetes Rollout History",
    tags=["k8s"],
    annotations={"readOnlyHint": True},
)
async def k8s_rollout_history(
    name: str,
    resource_type: str = Field(description="'deployment', 'daemonset', or 'statefulset'"),
    namespace: Optional[str] = Field(default="default"),
    revision: Optional[int] = Field(
        default=None,
        description="Omit for all revisions",
    ),
) -> ToolOutput:
    """View Kubernetes resource rollout history."""
    valid_resource_types = ["deployment", "daemonset", "statefulset"]
    if resource_type.lower() not in valid_resource_types:
        raise ValueError(
            f"Invalid resource_type '{resource_type}'. Must be one of: {', '.join(valid_resource_types)}"
        )

    cmd = f"rollout history {resource_type.lower()}/{name}"

    if namespace:
        cmd += f" -n {namespace}"

    if revision is not None:
        cmd += f" --revision={revision}"

    return await run_kubectl_command(cmd)


@mcp.tool(
    title="Get Kubernetes Cluster Information",
    tags=["k8s"],
    annotations={"readOnlyHint": True},
)
async def k8s_cluster_info() -> ToolOutput:
    """Get Kubernetes cluster info."""
    return await run_kubectl_command("cluster-info")


@mcp.tool(title="Cordon Kubernetes Node", tags=["k8s"], annotations={"readOnlyHint": False})
async def k8s_cordon(
    node_name: str,
) -> ToolOutput:
    """Cordon Kubernetes node, prevent new pod scheduling."""
    return await run_kubectl_command(f"cordon {node_name}")


@mcp.tool(title="Uncordon Kubernetes Node", tags=["k8s"], annotations={"readOnlyHint": False})
async def k8s_uncordon(
    node_name: str,
) -> ToolOutput:
    """Uncordon Kubernetes node, allow new pod scheduling."""
    return await run_kubectl_command(f"uncordon {node_name}")


@mcp.tool(
    title="Drain Kubernetes Node",
    tags=["k8s"],
    annotations={"readOnlyHint": False, "destructiveHint": True},
)
async def k8s_drain(
    node_name: str,
    ignore_daemonsets: Optional[bool] = Field(
        default=True, description="Skip DaemonSet-managed pods"
    ),
    delete_emptydir_data: Optional[bool] = Field(
        default=False, description="Delete pods using emptyDir volumes"
    ),
) -> ToolOutput:
    """Drain Kubernetes node, evict all pods."""
    cmd = f"drain {node_name}"
    if ignore_daemonsets:
        cmd += " --ignore-daemonsets"
    if delete_emptydir_data:
        cmd += " --delete-emptydir-data"
    return await run_kubectl_command(cmd)


@mcp.tool(title="Run Kubernetes Pod", tags=["k8s"], annotations={"readOnlyHint": False})
async def k8s_run_pod(
    name: str,
    image: str,
    namespace: Optional[str] = Field(default="default"),
    command: Optional[str] = Field(default=None, description="Command to run in the pod"),
) -> ToolOutput:
    """Run temporary pod in Kubernetes cluster."""
    args = ["run", name, f"--image={image}"]
    if isinstance(namespace, str) and namespace:
        args.extend(["-n", namespace])
    if isinstance(command, str) and command:
        args.append("--command")
        args.append("--")
        args.extend(shlex.split(command))
    return await run_command("kubectl", args)


@mcp.tool(
    title="Execute Command in Kubernetes Pod",
    tags=["k8s"],
    annotations={"readOnlyHint": False},
)
async def k8s_exec(
    pod_name: str,
    command: str,
    namespace: Optional[str] = Field(default="default"),
    container_name: Optional[str] = Field(
        default=None, description="Container to exec into. Required for multi-container pods."
    ),
) -> ToolOutput:
    """Execute command inside Kubernetes pod."""
    args = ["exec", pod_name]
    if isinstance(namespace, str) and namespace:
        args.extend(["-n", namespace])
    if isinstance(container_name, str) and container_name:
        args.extend(["-c", container_name])
    args.append("--")
    args.extend(shlex.split(command))
    return await run_command("kubectl", args)


@mcp.tool(
    title="Port Forward to Kubernetes Resource",
    tags=["k8s"],
    annotations={"readOnlyHint": False},
)
async def k8s_port_forward(
    resource_name: str,
    ports: str = Field(description="Format: 'local_port:remote_port'"),
    namespace: Optional[str] = Field(default="default"),
    resource_type: Optional[str] = Field(
        default="pod", description="'pod', 'service', 'deployment'"
    ),
) -> ToolOutput:
    """Port forward to Kubernetes resource."""
    resource_spec = f"{resource_type}/{resource_name}" if resource_type != "pod" else resource_name
    return await run_kubectl_command(
        f"port-forward {resource_spec} {ports} {f'-n {namespace}' if namespace else ''}"
    )


def build_kubectl_top_args(
    resource_type: str,
    name: Optional[str] = None,
    namespace: Optional[str] = None,
    all_namespaces: Optional[bool] = None,
    containers: Optional[bool] = None,
    label_selector: Optional[str] = None,
    sort_by: Optional[str] = None,
    no_headers: Optional[bool] = None,
) -> list[str]:
    """Build kubectl top command arguments from parameters."""
    args = ["top", resource_type]

    if name:
        args.append(name)

    if all_namespaces:
        args.append("-A")
    elif namespace:
        args.extend(["-n", namespace])

    if containers:
        args.append("--containers")

    if no_headers:
        args.append("--no-headers")

    if label_selector:
        args.extend(["-l", label_selector])

    if sort_by:
        if sort_by not in ["cpu", "memory"]:
            raise ValueError(f"sort_by must be 'cpu' or 'memory', got: {sort_by}")
        args.extend(["--sort-by", sort_by])

    return args


@mcp.tool(
    title="Get Kubernetes Pod Resource Usage",
    tags=["k8s", "metrics"],
    annotations={"readOnlyHint": True},
)
async def k8s_top_pods(
    pod_name: Optional[str] = Field(default=None),
    namespace: Optional[str] = Field(default=None),
    all_namespaces: Optional[bool] = Field(default=False, description="Query all namespaces"),
    show_containers: Optional[bool] = Field(
        default=False, description="Show container-level metrics"
    ),
    label_selector: Optional[str] = Field(default=None, description="e.g. 'app=nginx'"),
    sort_by: Optional[str] = Field(default=None, description="'cpu' or 'memory'"),
    no_headers: Optional[bool] = Field(default=False, description="Suppress column headers"),
) -> ToolOutput:
    """Get Kubernetes pod resource usage metrics."""
    if namespace and all_namespaces:
        raise ValueError("namespace and all_namespaces are mutually exclusive")

    args = build_kubectl_top_args(
        resource_type="pods",
        name=pod_name,
        namespace=namespace,
        all_namespaces=all_namespaces,
        containers=show_containers,
        label_selector=label_selector,
        sort_by=sort_by,
        no_headers=no_headers,
    )

    return await run_command("kubectl", args)


@mcp.tool(
    title="Get Kubernetes Node Resource Usage",
    tags=["k8s", "metrics"],
    annotations={"readOnlyHint": True},
)
async def k8s_top_nodes(
    node_name: Optional[str] = Field(default=None),
    sort_by: Optional[str] = Field(default=None, description="'cpu' or 'memory'"),
    label_selector: Optional[str] = Field(default=None, description="e.g. 'role=worker'"),
    no_headers: Optional[bool] = Field(default=False, description="Suppress column headers"),
) -> ToolOutput:
    """Get Kubernetes node resource usage metrics."""
    if node_name and label_selector:
        raise ValueError("node_name and label_selector are mutually exclusive")

    args = build_kubectl_top_args(
        resource_type="nodes",
        name=node_name,
        sort_by=sort_by,
        label_selector=label_selector,
        no_headers=no_headers,
    )

    return await run_command("kubectl", args)
