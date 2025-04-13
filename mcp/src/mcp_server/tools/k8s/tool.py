"""Kubernetes tool implementation."""

from typing import Dict, Any, Optional
from tools.common.models import (
    ToolConfig,
    ToolResponse,
    ParameterSchema,
)
from tools.common.mcp import MCPExecutor
from tools.utils.helpers import (
    create_tool_response,
    parse_resource_identifier,
    validate_namespace,
    parse_label_selector,
    parse_command_args,
)


class KubernetesConfig(ToolConfig):
    """Kubernetes tool configuration."""

    def __init__(self):
        """Initialize Kubernetes tool config."""
        super().__init__(
            name="kubectl",
            description="Kubernetes command-line tool",
            commands=[
                "get",
                "describe",
                "apply",
                "delete",
                "logs",
                "exec",
                "scale",
                "rollout",
                "port-forward",
                "explain",
                "api-resources",
                "events",
                "config",
                "patch",
                "label",
                "annotate",
                "wait",
                "create",
            ],
            permissions=["read", "write"],
            parameters=[
                ParameterSchema(
                    name="resource_type",
                    type="string",
                    description="The type of resource to operate on (pod, deployment, service, etc.)",
                    required=True,
                ),
                ParameterSchema(
                    name="ns",
                    type="string",
                    description="The namespace to operate in",
                    required=False,
                    aliases=["namespace"],
                ),
                ParameterSchema(
                    name="name",
                    type="string",
                    description="The name of the resource",
                    required=False,
                ),
                ParameterSchema(
                    name="all_namespaces",
                    type="boolean",
                    description="Whether to operate across all namespaces",
                    required=False,
                    default=False,
                ),
                ParameterSchema(
                    name="output",
                    type="string",
                    description="The output format (json, yaml, wide)",
                    required=False,
                    default="json",
                ),
                ParameterSchema(
                    name="labels",
                    type="dict",
                    description="Label selectors for filtering resources",
                    required=False,
                ),
                ParameterSchema(
                    name="field_selectors",
                    type="dict",
                    description="Field selectors for filtering resources",
                    required=False,
                ),
            ],
        )


class KubernetesTool:
    """Kubernetes tool implementation."""

    def __init__(self):
        """Initialize Kubernetes tool."""
        self.config = KubernetesConfig()

    async def execute(
        self,
        command: str,
        args: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> ToolResponse:
        """Execute a Kubernetes command.

        Args:
            command: Command to execute
            args: Command arguments
            context: Additional context

        Returns:
            ToolResponse object
        """
        try:
            # Validate command
            if command not in self.config.commands:
                raise ValueError(f"Invalid command: {command}")

            # Execute command based on type
            if command == "get":
                return await self._get_resources(args)
            elif command == "describe":
                return await self._describe_resource(args)
            elif command == "apply":
                return await self._apply_resource(args)
            elif command == "delete":
                return await self._delete_resource(args)
            elif command == "logs":
                return await self._get_logs(args)
            elif command == "exec":
                return await self._exec_command(args)
            elif command == "scale":
                return await self._scale_resource(args)
            elif command == "rollout":
                return await self._manage_rollout(args)
            elif command == "port-forward":
                return await self._port_forward(args)
            elif command == "explain":
                return await self._explain_resource(args)
            elif command == "api-resources":
                return await self._list_api_resources(args)
            elif command == "events":
                return await self._get_events(args)
            elif command == "config":
                return await self._manage_config(args)
            elif command == "patch":
                return await self._patch_resource(args)
            elif command == "label":
                return await self._manage_labels(args)
            elif command == "annotate":
                return await self._manage_annotations(args)
            elif command == "wait":
                return await self._wait_for_condition(args)
            elif command == "create":
                return await self._create_resource(args)

        except Exception as e:
            return create_tool_response(
                tool=self.config.name, command=command, error=str(e)
            )

    async def _get_resources(self, args: Dict[str, Any]) -> ToolResponse:
        """Get Kubernetes resources."""
        resource_type = args.get(
            "resource_type", "pods"
        )  # Default to pods if not specified
        namespace = validate_namespace(args.get("ns"))  # Use ns instead of namespace
        labels = args.get("labels", {})

        cmd_args = {"namespace": namespace, "output": args.get("output", "json")}

        if labels:
            cmd_args["selector"] = parse_label_selector(labels)

        # Execute kubectl get command through MCP
        result = await self._execute_kubectl(f"get {resource_type}", cmd_args)

        return create_tool_response(tool=self.config.name, command="get", result=result)

    async def _describe_resource(self, args: Dict[str, Any]) -> ToolResponse:
        """Describe a Kubernetes resource."""
        resource = parse_resource_identifier(args["resource"])
        namespace = validate_namespace(resource.namespace)

        result = await self._execute_kubectl(
            f"describe {resource.kind} {resource.name}", {"namespace": namespace}
        )

        return create_tool_response(
            tool=self.config.name, command="describe", result=result
        )

    async def _apply_resource(self, args: Dict[str, Any]) -> ToolResponse:
        """Apply a Kubernetes resource."""
        manifest = args["manifest"]

        result = await self._execute_kubectl(
            "apply", {"filename": "-"}, input_data=manifest
        )

        return create_tool_response(
            tool=self.config.name, command="apply", result=result
        )

    async def _delete_resource(self, args: Dict[str, Any]) -> ToolResponse:
        """Delete a Kubernetes resource."""
        resource = parse_resource_identifier(args["resource"])
        namespace = validate_namespace(resource.namespace)

        result = await self._execute_kubectl(
            f"delete {resource.kind} {resource.name}", {"namespace": namespace}
        )

        return create_tool_response(
            tool=self.config.name, command="delete", result=result
        )

    async def _get_logs(self, args: Dict[str, Any]) -> ToolResponse:
        """Get logs from a pod."""
        pod = args["pod"]
        namespace = validate_namespace(args.get("namespace"))
        container = args.get("container")

        cmd_args = {
            "namespace": namespace,
            "follow": args.get("follow", False),
            "tail": args.get("tail", 100),
        }

        if container:
            cmd_args["container"] = container

        result = await self._execute_kubectl(f"logs {pod}", cmd_args)

        return create_tool_response(
            tool=self.config.name, command="logs", result=result
        )

    async def _exec_command(self, args: Dict[str, Any]) -> ToolResponse:
        """Execute a command in a container."""
        pod = args["pod"]
        command = args["command"]
        namespace = validate_namespace(args.get("namespace"))
        container = args.get("container")

        cmd_args = {"namespace": namespace}

        if container:
            cmd_args["container"] = container

        result = await self._execute_kubectl(f"exec {pod} -- {command}", cmd_args)

        return create_tool_response(
            tool=self.config.name, command="exec", result=result
        )

    async def _scale_resource(self, args: Dict[str, Any]) -> ToolResponse:
        """Scale a resource."""
        resource = parse_resource_identifier(args["resource"])
        replicas = args["replicas"]
        namespace = validate_namespace(resource.namespace)

        result = await self._execute_kubectl(
            f"scale {resource.kind} {resource.name}",
            {"namespace": namespace, "replicas": replicas},
        )

        return create_tool_response(
            tool=self.config.name, command="scale", result=result
        )

    async def _manage_rollout(self, args: Dict[str, Any]) -> ToolResponse:
        """Manage resource rollout."""
        resource = parse_resource_identifier(args["resource"])
        subcommand = args["subcommand"]  # status, history, undo, etc.
        namespace = validate_namespace(resource.namespace)

        result = await self._execute_kubectl(
            f"rollout {subcommand} {resource.kind} {resource.name}",
            {"namespace": namespace},
        )

        return create_tool_response(
            tool=self.config.name, command=f"rollout {subcommand}", result=result
        )

    async def _port_forward(self, args: Dict[str, Any]) -> ToolResponse:
        """Forward ports to a resource."""
        resource = parse_resource_identifier(args["resource"])
        ports = args["ports"]  # Format: "local:remote"
        namespace = validate_namespace(resource.namespace)

        result = await self._execute_kubectl(
            f"port-forward {resource.kind}/{resource.name} {ports}",
            {"namespace": namespace},
        )

        return create_tool_response(
            tool=self.config.name, command="port-forward", result=result
        )

    async def _explain_resource(self, args: Dict[str, Any]) -> ToolResponse:
        """Get explanation of Kubernetes resources."""
        resource = args.get("resource")
        if not resource:
            raise ValueError("Resource type is required")

        recursive = args.get("recursive", False)
        cmd_args = {"recursive": recursive} if recursive else {}

        result = await self._execute_kubectl(f"explain {resource}", cmd_args)
        return create_tool_response(
            tool=self.config.name, command="explain", result=result
        )

    async def _list_api_resources(self, args: Dict[str, Any]) -> ToolResponse:
        """List available API resources."""
        cmd_args = {
            "output": args.get("output", "wide"),
            "namespaced": args.get("namespaced", None),
            "verbs": args.get("verbs", None),
        }
        result = await self._execute_kubectl("api-resources", cmd_args)
        return create_tool_response(
            tool=self.config.name, command="api-resources", result=result
        )

    async def _get_events(self, args: Dict[str, Any]) -> ToolResponse:
        """Get Kubernetes events."""
        namespace = validate_namespace(args.get("namespace"))
        field_selector = args.get("field_selector")
        labels = args.get("labels")

        cmd_args = {
            "namespace": namespace,
            "output": args.get("output", "wide"),
            "field-selector": field_selector,
            "selector": parse_label_selector(labels) if labels else None,
        }
        result = await self._execute_kubectl("get events", cmd_args)
        return create_tool_response(
            tool=self.config.name, command="events", result=result
        )

    async def _manage_config(self, args: Dict[str, Any]) -> ToolResponse:
        """Manage kubeconfig."""
        subcommand = args.get("subcommand", "view")
        if subcommand not in ["view", "get-contexts", "use-context", "set-context"]:
            raise ValueError(f"Invalid config subcommand: {subcommand}")

        cmd_args = parse_command_args(args)
        result = await self._execute_kubectl(f"config {subcommand}", cmd_args)
        return create_tool_response(
            tool=self.config.name, command="config", result=result
        )

    async def _patch_resource(self, args: Dict[str, Any]) -> ToolResponse:
        """Patch a Kubernetes resource."""
        resource = args.get("resource")
        if not resource:
            raise ValueError("Resource is required")

        patch_data = args.get("patch")
        if not patch_data:
            raise ValueError("Patch data is required")

        namespace = validate_namespace(args.get("namespace"))
        patch_type = args.get("type", "strategic")

        cmd_args = {
            "namespace": namespace,
            "type": patch_type,
            "patch": patch_data,
        }
        result = await self._execute_kubectl(f"patch {resource}", cmd_args)
        return create_tool_response(
            tool=self.config.name, command="patch", result=result
        )

    async def _manage_labels(self, args: Dict[str, Any]) -> ToolResponse:
        """Manage resource labels."""
        resource = args.get("resource")
        if not resource:
            raise ValueError("Resource is required")

        namespace = validate_namespace(args.get("namespace"))
        labels = args.get("labels", {})
        overwrite = args.get("overwrite", False)
        remove = args.get("remove", [])

        cmd_args = {
            "namespace": namespace,
            "overwrite": overwrite,
        }

        # Handle label removal
        if remove:
            label_args = [f"{key}-" for key in remove]
        else:
            label_args = [f"{k}={v}" for k, v in labels.items()]

        result = await self._execute_kubectl(
            f"label {resource} {' '.join(label_args)}", cmd_args
        )
        return create_tool_response(
            tool=self.config.name, command="label", result=result
        )

    async def _manage_annotations(self, args: Dict[str, Any]) -> ToolResponse:
        """Manage resource annotations."""
        resource = args.get("resource")
        if not resource:
            raise ValueError("Resource is required")

        namespace = validate_namespace(args.get("namespace"))
        annotations = args.get("annotations", {})
        overwrite = args.get("overwrite", False)
        remove = args.get("remove", [])

        cmd_args = {
            "namespace": namespace,
            "overwrite": overwrite,
        }

        # Handle annotation removal
        if remove:
            annotation_args = [f"{key}-" for key in remove]
        else:
            annotation_args = [f"{k}={v}" for k, v in annotations.items()]

        result = await self._execute_kubectl(
            f"annotate {resource} {' '.join(annotation_args)}", cmd_args
        )
        return create_tool_response(
            tool=self.config.name, command="annotate", result=result
        )

    async def _wait_for_condition(self, args: Dict[str, Any]) -> ToolResponse:
        """Wait for a condition on a resource."""
        resource = args.get("resource")
        if not resource:
            raise ValueError("Resource is required")

        namespace = validate_namespace(args.get("namespace"))
        condition = args.get("condition", "Ready")
        timeout = args.get("timeout", "30s")

        cmd_args = {
            "namespace": namespace,
            "for": condition,
            "timeout": timeout,
        }

        result = await self._execute_kubectl(f"wait {resource}", cmd_args)
        return create_tool_response(
            tool=self.config.name, command="wait", result=result
        )

    async def _create_resource(self, args: Dict[str, Any]) -> ToolResponse:
        """Create a Kubernetes resource."""
        resource_type = args.get("resource_type")
        if not resource_type:
            raise ValueError("Resource type is required")

        namespace = validate_namespace(args.get("namespace"))
        name = args.get("name")
        image = args.get("image")  # For pods/deployments

        cmd_args = {
            "namespace": namespace,
        }

        if resource_type == "namespace":
            result = await self._execute_kubectl(f"create namespace {name}", {})
        elif resource_type in ["pod", "deployment"]:
            if not image:
                raise ValueError("Image is required for pod/deployment creation")
            result = await self._execute_kubectl(
                f"create {resource_type} {name} --image={image}", cmd_args
            )
        else:
            # For other resource types, expect a YAML/JSON definition
            definition = args.get("definition")
            if not definition:
                raise ValueError("Resource definition is required")
            result = await self._execute_kubectl(
                "create -f -", cmd_args, input_data=definition
            )

        return create_tool_response(
            tool=self.config.name, command="create", result=result
        )

    async def _execute_kubectl(
        self, command: str, args: Dict[str, Any], input_data: Optional[Any] = None
    ) -> Any:
        """Execute a kubectl command through MCP."""
        executor = MCPExecutor()
        return await executor.execute(
            tool="kubectl", command=command, args=args, input_data=input_data
        )
