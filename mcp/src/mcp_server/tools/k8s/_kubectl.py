"""Kubernetes tools implementation."""

from typing import Annotated, Optional
from autogen_core.tools import FunctionTool
import os
import tempfile

from .._utils import (
    create_typed_fn_tool,
    run_command,
    exec_create_manifest,
    ManifestError,
)


async def _run_kubectl_command(command: str) -> str:
    """Run a kubectl command and return its output."""
    # Split the command and remove empty strings
    cmd_parts = [part for part in command.split(" ") if part]
    return await run_command("kubectl", cmd_parts)


async def _get_pod_logs(
    pod_name: Annotated[str, "The name of the pod to get logs from"],
    namespace: Annotated[
        Optional[str], "The namespace of the pod to get logs from"
    ] = "default",
    num_lines: Annotated[
        Optional[int], "The number of lines to get from the logs"
    ] = 50,
) -> str:
    """Get logs from a pod."""
    return await _run_kubectl_command(
        f"logs {pod_name} {f'-n {namespace}' if namespace else ''} --tail {num_lines}"
    )


async def _get_resources(
    name: Annotated[
        Optional[str],
        "The name of the resource to get information about. If not provided, all resources of the given type will be returned. alias: resource_name",
    ] = None,
    resource_type: Annotated[
        str,
        "The type of resource to get information about (deployment, service, pod, node, ...). 'all' is NOT an option, you must specify a resource type.",
    ] = None,
    all_namespaces: Annotated[
        Optional[bool], "Whether to get resources from all namespaces"
    ] = False,
    namespace: Annotated[
        Optional[str],
        "The namespace of the resource to get information about, if unset will default to the current namespace. alias: namespace",
    ] = None,
    output: Annotated[
        Optional[str], "The output format of the resource information"
    ] = None,
) -> str:
    """Get information about Kubernetes resources."""
    if not resource_type:
        raise ValueError("resource_type is required")

    if name and all_namespaces:
        # only use the name if provided, and ignore all_namespaces
        all_namespaces = False

    return await _run_kubectl_command(
        f"get {resource_type} {name if name else ''} {'-n' + namespace + ' ' if namespace else ''}{'-o' + output if output else ''} {'-A' if all_namespaces else ''}"
    )


async def _describe_resource(
    resource_type: Annotated[
        str, "The type of resource to describe (deployment, service, pod, node, ...)"
    ],
    name: Annotated[str, "The name of the resource to describe"],
    namespace: Annotated[Optional[str], "The namespace of the resource to describe"],
) -> str:
    """Describe a Kubernetes resource."""
    return await _run_kubectl_command(
        f"describe {resource_type} {name} {f'-n {namespace}' if namespace else ''}"
    )


async def _update_resource_container_images(
    resource_type: Annotated[
        str, "The type of resource to update (deployment, statefulset, daemonset, etc.)"
    ],
    resource_name: Annotated[str, "The name of the resource to update"],
    namespace: Annotated[Optional[str], "The namespace of the resource to update"],
    container_images: Annotated[
        str,
        "The container and image pairs to update. Format: 'container1=image1,container2=image2' or just 'container=image' for a single container",
    ],
) -> str:
    """Update the image of one or more containers in a Kubernetes resource."""
    return await _run_kubectl_command(
        f"set image {resource_type}/{resource_name} {container_images} {f'-n {namespace}' if namespace else ''}"
    )


async def _patch_resource(
    resource_type: Annotated[
        str, "The type of resource to patch (deployment, service, pod, hpa, node, ...)"
    ],
    resource_name: Annotated[str, "The name of the resource to patch"],
    namespace: Annotated[Optional[str], "The namespace of the resource to patch"],
    patch: Annotated[str, "The patch escaped JSON string to apply to the resource"],
) -> str:
    """Patch a Kubernetes resource."""
    patch_command = f"patch {resource_type} {resource_name} {f'-n {namespace}' if namespace else ''} --patch {patch} --type=merge"

    return await _run_kubectl_command(patch_command)


async def _rollout_restart_deployment(
    name: Annotated[str, "The name of the deployment to rollout"],
    namespace: Annotated[Optional[str], "The namespace of the deployment to rollout"],
) -> str:
    """Rollout a deployment."""
    return await _run_kubectl_command(
        f"rollout restart deployment/{name} {f'-n {namespace}' if namespace else ''}"
    )


async def _scale(
    resource_type: Annotated[
        str, "The type of resource to scale (deployment, statefulset, ...)"
    ],
    name: Annotated[str, "The name of the resource to scale"],
    replicas: Annotated[int, "The number of replicas to scale to"],
    namespace: Annotated[Optional[str], "The namespace of the resource to scale"],
) -> str:
    """Scale a Kubernetes resource."""
    return await _run_kubectl_command(
        f"scale {resource_type}/{name} --replicas={replicas} {f'-n {namespace} ' if namespace else ''}"
    )


async def _delete_resource(
    resource_type: Annotated[
        str, "The type of resource to delete (deployment, service, pod, node, ...)"
    ],
    name: Annotated[str, "The name of the resource to delete"],
    namespace: Annotated[Optional[str], "The namespace of the resource to delete"],
) -> str:
    """Delete a Kubernetes resource."""
    return await _run_kubectl_command(
        f"delete {resource_type} {name} {f'-n {namespace}' if namespace else ''}"
    )


async def _create_manifest(
    manifest_name: Annotated[
        str, "The name of the manifest file (should end with .yaml or .yml)"
    ],
    yaml_content: Annotated[str, "The YAML manifest content to save"],
) -> str:
    """Create a Kubernetes manifest file on the engine server."""
    try:
        return await exec_create_manifest(manifest_name, yaml_content)
    except ManifestError as e:
        raise ValueError(str(e))


async def _apply_manifest(
    manifest_path: Annotated[str, "The path to the manifest file to apply"],
    namespace: Annotated[
        Optional[str], "The namespace to apply the manifest to"
    ] = None,
) -> str:
    """Apply a Kubernetes manifest file."""
    manifest_path = os.path.join(
        tempfile.gettempdir(), "skyflo", "manifests", manifest_path
    )
    return await _run_kubectl_command(
        f"apply -f {manifest_path} {f'-n {namespace}' if namespace else ''}"
    )


async def _wait_for_x_seconds(seconds: Annotated[int, "The number of seconds to wait"]):
    """Wait for x seconds."""
    # The actual waiting is done in the engine server
    return "Done waiting"


async def _rollout_status(
    deployment_name: Annotated[
        str, "The name of the deployment to check rollout status"
    ],
    namespace: Annotated[Optional[str], "The namespace of the deployment"],
) -> str:
    """Get rollout status of a deployment."""
    return await _run_kubectl_command(
        f"rollout status deployment/{deployment_name} {f'-n {namespace}' if namespace else ''}"
    )


async def _get_cluster_info() -> str:
    """Get information about the Kubernetes cluster."""
    return await _run_kubectl_command("cluster-info")


async def _cordon_node(
    node_name: Annotated[str, "The name of the node to cordon"],
) -> str:
    """Mark a node as unschedulable."""
    return await _run_kubectl_command(f"cordon {node_name}")


async def _uncordon_node(
    node_name: Annotated[str, "The name of the node to uncordon"],
) -> str:
    """Mark a node as schedulable."""
    return await _run_kubectl_command(f"uncordon {node_name}")


async def _drain_node(
    node_name: Annotated[str, "The name of the node to drain"],
    ignore_daemonsets: Annotated[
        Optional[bool], "Whether to ignore DaemonSet-managed pods"
    ] = True,
) -> str:
    """Drain a node in preparation for maintenance."""
    return await _run_kubectl_command(
        f"drain {node_name} {f'--ignore-daemonsets' if ignore_daemonsets else ''}"
    )


async def _run_pod(
    pod_name: Annotated[str, "The name of the pod to create"],
    image: Annotated[str, "The container image to use"],
    restart_policy: Annotated[
        Optional[str], "The restart policy (Never, OnFailure, Always)"
    ] = None,
    namespace: Annotated[Optional[str], "The namespace to run the pod in"] = None,
) -> str:
    """Create a pod from a specified image."""
    return await _run_kubectl_command(
        f"run {pod_name} --image={image} {f'--restart={restart_policy}' if restart_policy else ''} {f'-n {namespace}' if namespace else ''}"
    )


async def _port_forward(
    pod_name: Annotated[str, "The name of the pod to port-forward to"],
    port_mapping: Annotated[str, "Port mapping in format localPort:podPort"],
    namespace: Annotated[Optional[str], "The namespace of the pod"],
) -> str:
    """Forward a local port to a port on a pod."""
    return await _run_kubectl_command(
        f"port-forward {pod_name} {port_mapping} {f'-n {namespace}' if namespace else ''}"
    )


# Create function tools with async support
get_pod_logs = FunctionTool(
    _get_pod_logs,
    description="Get logs from a pod in Kubernetes.",
    name="get_pod_logs",
)

get_resources = FunctionTool(
    _get_resources,
    description="Get information about resources in Kubernetes.",
    name="get_resources",
)

describe_resource = FunctionTool(
    _describe_resource,
    description="Describe a resource in Kubernetes.",
    name="describe_resource",
)

update_resource_container_images = FunctionTool(
    _update_resource_container_images,
    description="Update the image of one or more containers in a Kubernetes resource.",
    name="update_resource_container_images",
)

patch_resource = FunctionTool(
    _patch_resource,
    description="Patch a Kubernetes resource.",
    name="patch_resource",
)

scale = FunctionTool(
    _scale,
    description="Scale a resource in Kubernetes.",
    name="scale",
)

rollout_restart_deployment = FunctionTool(
    _rollout_restart_deployment,
    description="Rollout a deployment in Kubernetes.",
    name="rollout_restart_deployment",
)

delete_resource = FunctionTool(
    _delete_resource,
    description="Delete a resource in Kubernetes.",
    name="delete_resource",
)

create_manifest = FunctionTool(
    _create_manifest,
    description="Create a Kubernetes manifest file on the engine server.",
    name="create_manifest",
)

apply_manifest = FunctionTool(
    _apply_manifest,
    description="Apply a Kubernetes manifest file.",
    name="apply_manifest",
)

wait_for_x_seconds = FunctionTool(
    _wait_for_x_seconds,
    description="Wait for x seconds.",
    name="wait_for_x_seconds",
)

rollout_status = FunctionTool(
    _rollout_status,
    description="Get rollout status of a deployment.",
    name="rollout_status",
)

get_cluster_info = FunctionTool(
    _get_cluster_info,
    description="Get information about the Kubernetes cluster.",
    name="get_cluster_info",
)

cordon_node = FunctionTool(
    _cordon_node,
    description="Mark a node as unschedulable.",
    name="cordon_node",
)

uncordon_node = FunctionTool(
    _uncordon_node,
    description="Mark a node as schedulable.",
    name="uncordon_node",
)

drain_node = FunctionTool(
    _drain_node,
    description="Drain a node in preparation for maintenance.",
    name="drain_node",
)

run_pod = FunctionTool(
    _run_pod,
    description="Create a pod from a specified image.",
    name="run_pod",
)

port_forward = FunctionTool(
    _port_forward,
    description="Forward a local port to a port on a pod.",
    name="port_forward",
)

# Create typed tools
GetPodLogs, GetPodLogsConfig = create_typed_fn_tool(
    get_pod_logs, "engine.tools.k8s.GetPodLogs", "GetPodLogs"
)

GetResources, GetResourcesConfig = create_typed_fn_tool(
    get_resources, "engine.tools.k8s.GetResources", "GetResources"
)

DescribeResource, DescribeResourceConfig = create_typed_fn_tool(
    describe_resource, "engine.tools.k8s.DescribeResource", "DescribeResource"
)

UpdateContainerImage, UpdateContainerImageConfig = create_typed_fn_tool(
    update_resource_container_images,
    "engine.tools.k8s.UpdateContainerImage",
    "UpdateContainerImage",
)

PatchResource, PatchResourceConfig = create_typed_fn_tool(
    patch_resource, "engine.tools.k8s.PatchResource", "PatchResource"
)

Scale, ScaleConfig = create_typed_fn_tool(scale, "engine.tools.k8s.Scale", "Scale")

RolloutRestartDeployment, RolloutRestartDeploymentConfig = create_typed_fn_tool(
    rollout_restart_deployment,
    "engine.tools.k8s.RolloutRestartDeployment",
    "RolloutRestartDeployment",
)

DeleteResource, DeleteResourceConfig = create_typed_fn_tool(
    delete_resource,
    "engine.tools.k8s.DeleteResource",
    "DeleteResource",
)

CreateManifest, CreateManifestConfig = create_typed_fn_tool(
    create_manifest, "engine.tools.k8s.CreateManifest", "CreateManifest"
)

ApplyManifest, ApplyManifestConfig = create_typed_fn_tool(
    apply_manifest, "engine.tools.k8s.ApplyManifest", "ApplyManifest"
)

WaitForXSeconds, WaitForXSecondsConfig = create_typed_fn_tool(
    wait_for_x_seconds, "engine.tools.k8s.WaitForXSeconds", "WaitForXSeconds"
)

RolloutStatus, RolloutStatusConfig = create_typed_fn_tool(
    rollout_status, "engine.tools.k8s.RolloutStatus", "RolloutStatus"
)

GetClusterInfo, GetClusterInfoConfig = create_typed_fn_tool(
    get_cluster_info, "engine.tools.k8s.GetClusterInfo", "GetClusterInfo"
)

CordonNode, CordonNodeConfig = create_typed_fn_tool(
    cordon_node, "engine.tools.k8s.CordonNode", "CordonNode"
)

UncordonNode, UncordonNodeConfig = create_typed_fn_tool(
    uncordon_node, "engine.tools.k8s.UncordonNode", "UncordonNode"
)

DrainNode, DrainNodeConfig = create_typed_fn_tool(
    drain_node, "engine.tools.k8s.DrainNode", "DrainNode"
)

RunPod, RunPodConfig = create_typed_fn_tool(
    run_pod, "engine.tools.k8s.RunPod", "RunPod"
)

PortForward, PortForwardConfig = create_typed_fn_tool(
    port_forward, "engine.tools.k8s.PortForward", "PortForward"
)
