"""Argo tool implementation."""

from typing import Dict, Any, Optional
from tools.common.models import ToolConfig, ToolResponse
from tools.common.mcp import MCPExecutor
from tools.utils.helpers import (
    create_tool_response,
    validate_namespace,
    parse_resource_identifier,
)


class ArgoConfig(ToolConfig):
    """Argo tool configuration."""

    def __init__(self):
        """Initialize Argo tool config."""
        super().__init__(
            name="argo",
            description="Argo CD and Rollouts management",
            commands=[
                "promote",
                "abort",
                "retry",
                "status",
                "list",
                "set",
                "undo",
                "pause",
                "resume",
            ],
            permissions=["read", "write"],
        )


class ArgoTool:
    """Argo tool implementation."""

    def __init__(self):
        """Initialize Argo tool."""
        self.config = ArgoConfig()

    async def execute(
        self,
        command: str,
        args: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> ToolResponse:
        """Execute an Argo command.

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
            if command == "promote":
                return await self._promote_rollout(args)
            elif command == "abort":
                return await self._abort_rollout(args)
            elif command == "retry":
                return await self._retry_rollout(args)
            elif command == "status":
                return await self._get_status(args)
            elif command == "list":
                return await self._list_rollouts(args)
            elif command == "set":
                return await self._set_rollout(args)
            elif command == "undo":
                return await self._undo_rollout(args)
            elif command == "pause":
                return await self._pause_rollout(args)
            elif command == "resume":
                return await self._resume_rollout(args)
            elif command == "restart":
                return await self._restart_rollout(args)

        except Exception as e:
            return create_tool_response(
                tool=self.config.name, command=command, error=str(e)
            )

    async def _promote_rollout(self, args: Dict[str, Any]) -> ToolResponse:
        """Promote an Argo rollout.

        Args:
            args: Promotion arguments
        """
        rollout = parse_resource_identifier(args["rollout"])
        namespace = validate_namespace(rollout.namespace)

        cmd_args = {
            "namespace": namespace,
            "full": args.get("full", False),  # Skip analysis, pauses, and steps
        }

        result = await self._execute_argo(f"promote {rollout.name}", cmd_args)

        return create_tool_response(
            tool=self.config.name, command="promote", result=result
        )

    async def _abort_rollout(self, args: Dict[str, Any]) -> ToolResponse:
        """Abort an Argo rollout."""
        rollout = parse_resource_identifier(args["rollout"])
        namespace = validate_namespace(rollout.namespace)

        result = await self._execute_argo(
            f"abort {rollout.name}", {"namespace": namespace}
        )

        return create_tool_response(
            tool=self.config.name, command="abort", result=result
        )

    async def _retry_rollout(self, args: Dict[str, Any]) -> ToolResponse:
        """Retry an Argo rollout."""
        rollout = parse_resource_identifier(args["rollout"])
        namespace = validate_namespace(rollout.namespace)

        result = await self._execute_argo(
            f"retry {rollout.name}", {"namespace": namespace}
        )

        return create_tool_response(
            tool=self.config.name, command="retry", result=result
        )

    async def _get_status(self, args: Dict[str, Any]) -> ToolResponse:
        """Get Argo rollout status."""
        rollout = parse_resource_identifier(args["rollout"])
        namespace = validate_namespace(rollout.namespace)

        result = await self._execute_argo(
            f"status {rollout.name}",
            {
                "namespace": namespace,
                "output": "json",
                "watch": args.get("watch", False),
            },
        )

        return create_tool_response(
            tool=self.config.name, command="status", result=result
        )

    async def _list_rollouts(self, args: Dict[str, Any]) -> ToolResponse:
        """List Argo rollouts."""
        namespace = args.get("namespace", "")  # Empty string means all namespaces

        cmd_args = {"all-namespaces": not namespace, "output": "json"}

        if namespace:
            cmd_args["namespace"] = namespace

        result = await self._execute_argo("list", cmd_args)

        return create_tool_response(
            tool=self.config.name, command="list", result=result
        )

    async def _set_rollout(self, args: Dict[str, Any]) -> ToolResponse:
        """Set rollout parameters."""
        rollout = parse_resource_identifier(args["rollout"])
        namespace = validate_namespace(rollout.namespace)
        image = args.get("image")

        cmd_args = {"namespace": namespace}

        if image:
            cmd_args["image"] = image

        result = await self._execute_argo(f"set {rollout.name}", cmd_args)

        return create_tool_response(tool=self.config.name, command="set", result=result)

    async def _undo_rollout(self, args: Dict[str, Any]) -> ToolResponse:
        """Undo a rollout change."""
        rollout = parse_resource_identifier(args["rollout"])
        namespace = validate_namespace(rollout.namespace)
        revision = args.get("revision")

        cmd_args = {"namespace": namespace}
        if revision:
            cmd_args["revision"] = revision

        result = await self._execute_argo(f"undo {rollout.name}", cmd_args)

        return create_tool_response(
            tool=self.config.name, command="undo", result=result
        )

    async def _pause_rollout(self, args: Dict[str, Any]) -> ToolResponse:
        """Pause a rollout."""
        rollout = parse_resource_identifier(args["rollout"])
        namespace = validate_namespace(rollout.namespace)

        result = await self._execute_argo(
            f"pause {rollout.name}", {"namespace": namespace}
        )

        return create_tool_response(
            tool=self.config.name, command="pause", result=result
        )

    async def _resume_rollout(self, args: Dict[str, Any]) -> ToolResponse:
        """Resume a paused rollout."""
        rollout = parse_resource_identifier(args["rollout"])
        namespace = validate_namespace(rollout.namespace)

        result = await self._execute_argo(
            f"resume {rollout.name}", {"namespace": namespace}
        )

        return create_tool_response(
            tool=self.config.name, command="resume", result=result
        )

    async def _restart_rollout(self, args: Dict[str, Any]) -> ToolResponse:
        """Restart a rollout."""
        rollout = parse_resource_identifier(args["rollout"])
        namespace = validate_namespace(rollout.namespace)

        result = await self._execute_argo(
            f"restart {rollout.name}", {"namespace": namespace}
        )

        return create_tool_response(
            tool=self.config.name, command="restart", result=result
        )

    async def _execute_argo(
        self, command: str, args: Dict[str, Any], input_data: Optional[Any] = None
    ) -> Any:
        """Execute an argo command through MCP."""
        executor = MCPExecutor()
        return await executor.execute(
            tool="argo", command=command, args=args, input_data=input_data
        )
