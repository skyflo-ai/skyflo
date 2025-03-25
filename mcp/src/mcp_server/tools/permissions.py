"""Permission management for Skyflo.ai MCP Server tools."""

from enum import Enum
from typing import Set, Dict
from dataclasses import dataclass


class OperationType(Enum):
    """Types of operations that can be performed by tools."""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    SCALE = "scale"
    ROLLOUT = "rollout"


@dataclass
class ToolPermission:
    """Permission configuration for a tool."""

    operation_type: OperationType
    description: str
    requires_approval: bool = False


# Define permissions for each tool category
KUBERNETES_PERMISSIONS: Dict[str, ToolPermission] = {
    "get_pod_logs": ToolPermission(OperationType.READ, "Get logs from pods"),
    "get_resources": ToolPermission(OperationType.READ, "Read Kubernetes resources"),
    "describe_resource": ToolPermission(
        OperationType.READ, "Describe Kubernetes resources"
    ),
    "create_manifest": ToolPermission(
        OperationType.WRITE, "Create Kubernetes manifest", requires_approval=True
    ),
    "apply_manifest": ToolPermission(
        OperationType.WRITE, "Apply Kubernetes manifest", requires_approval=True
    ),
    "update_resource_container_images": ToolPermission(
        OperationType.WRITE,
        "Update Kubernetes resource container images",
        requires_approval=True,
    ),
    "patch_resource": ToolPermission(
        OperationType.WRITE, "Modify Kubernetes resources", requires_approval=True
    ),
    "scale": ToolPermission(
        OperationType.SCALE, "Scale Kubernetes resources", requires_approval=True
    ),
    "rollout_restart_deployment": ToolPermission(
        OperationType.ROLLOUT, "Restart Kubernetes deployments", requires_approval=True
    ),
    "delete_resource": ToolPermission(
        OperationType.DELETE, "Delete Kubernetes resources", requires_approval=True
    ),
    "wait_for_x_seconds": ToolPermission(
        OperationType.READ, "Wait for x seconds", requires_approval=False
    ),
    "rollout_status": ToolPermission(
        OperationType.READ, "Check rollout status of deployments"
    ),
    "get_cluster_info": ToolPermission(OperationType.READ, "Get cluster information"),
    "cordon_node": ToolPermission(
        OperationType.WRITE, "Mark node as unschedulable", requires_approval=True
    ),
    "uncordon_node": ToolPermission(
        OperationType.WRITE, "Mark node as schedulable", requires_approval=True
    ),
    "drain_node": ToolPermission(
        OperationType.WRITE, "Drain node for maintenance", requires_approval=True
    ),
    "run_pod": ToolPermission(
        OperationType.WRITE, "Create a pod from an image", requires_approval=True
    ),
    "port_forward": ToolPermission(
        OperationType.READ, "Forward local port to pod", requires_approval=True
    ),
}

ARGO_PERMISSIONS: Dict[str, ToolPermission] = {
    "get_rollouts": ToolPermission(OperationType.READ, "List Argo rollouts"),
    "promote_rollout": ToolPermission(
        OperationType.ROLLOUT, "Promote an Argo rollout", requires_approval=True
    ),
    "pause_rollout": ToolPermission(
        OperationType.ROLLOUT, "Pause an Argo rollout", requires_approval=True
    ),
    "set_rollout_image": ToolPermission(
        OperationType.WRITE,
        "Set container image in Argo rollout",
        requires_approval=True,
    ),
    "rollout_restart": ToolPermission(
        OperationType.ROLLOUT, "Restart an Argo rollout", requires_approval=True
    ),
}

HELM_PERMISSIONS: Dict[str, ToolPermission] = {
    "helm_list_releases": ToolPermission(OperationType.READ, "List Helm releases"),
    "generate_helm_values": ToolPermission(
        OperationType.READ, "Generate Helm values file"
    ),
    "helm_repo_update": ToolPermission(OperationType.READ, "Update Helm repositories"),
    "helm_repo_add": ToolPermission(
        OperationType.WRITE, "Add Helm repository", requires_approval=True
    ),
    "helm_repo_remove": ToolPermission(
        OperationType.DELETE, "Remove Helm repository", requires_approval=True
    ),
    "helm_install": ToolPermission(
        OperationType.WRITE, "Install Helm chart", requires_approval=True
    ),
    "helm_install_with_values": ToolPermission(
        OperationType.WRITE,
        "Install Helm chart with custom values",
        requires_approval=True,
    ),
}


def requires_approval(tool_name: str, category: str) -> bool:
    """Check if a tool requires approval based on its permissions.

    Args:
        tool_name: Name of the tool
        category: Tool category (kubernetes, argo, helm)

    Returns:
        bool: Whether the tool requires approval
    """
    permissions_map = {
        "kubernetes": KUBERNETES_PERMISSIONS,
        "argo": ARGO_PERMISSIONS,
        "helm": HELM_PERMISSIONS,
    }

    if category not in permissions_map:
        return False

    permission = permissions_map[category].get(tool_name)
    return permission.requires_approval if permission else False
