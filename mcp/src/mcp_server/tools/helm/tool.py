"""Helm tool implementation."""

from typing import Dict, Any, Optional
from tools.common.models import ToolConfig, ToolResponse
from tools.common.mcp import MCPExecutor
from tools.utils.helpers import (
    create_tool_response,
    validate_namespace,
)


class HelmConfig(ToolConfig):
    """Helm tool configuration."""

    def __init__(self):
        """Initialize Helm tool config."""
        super().__init__(
            name="helm",
            description="Helm package manager",
            commands=[
                "install",
                "upgrade",
                "rollback",
                "uninstall",
                "list",
                "status",
                "repo",
                "get",
            ],
            permissions=["read", "write"],
        )


class HelmTool:
    """Helm tool implementation."""

    def __init__(self):
        """Initialize Helm tool."""
        self.config = HelmConfig()

    async def execute(
        self,
        command: str,
        args: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> ToolResponse:
        """Execute a Helm command.

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
            if command == "install":
                return await self._install_chart(args)
            elif command == "upgrade":
                return await self._upgrade_release(args)
            elif command == "rollback":
                return await self._rollback_release(args)
            elif command == "uninstall":
                return await self._uninstall_release(args)
            elif command == "list":
                return await self._list_releases(args)
            elif command == "status":
                return await self._get_status(args)
            elif command == "repo":
                return await self._manage_repo(args)
            elif command == "get":
                return await self._get_release_info(args)

        except Exception as e:
            return create_tool_response(
                tool=self.config.name, command=command, error=str(e)
            )

    async def _install_chart(self, args: Dict[str, Any]) -> ToolResponse:
        """Install a Helm chart.

        Args:
            args: Installation arguments
        """
        release_name = args["release"]
        chart = args["chart"]
        namespace = validate_namespace(args.get("namespace"))
        values = args.get("values", {})

        cmd_args = {"namespace": namespace, "create-namespace": True, "wait": True}

        if values:
            cmd_args["values"] = values

        result = await self._execute_helm(f"install {release_name} {chart}", cmd_args)

        return create_tool_response(
            tool=self.config.name, command="install", result=result
        )

    async def _upgrade_release(self, args: Dict[str, Any]) -> ToolResponse:
        """Upgrade a Helm release."""
        release_name = args["release"]
        chart = args["chart"]
        namespace = validate_namespace(args.get("namespace"))
        values = args.get("values", {})

        cmd_args = {
            "namespace": namespace,
            "install": True,  # Create if doesn't exist
            "wait": True,
        }

        if values:
            cmd_args["values"] = values

        result = await self._execute_helm(f"upgrade {release_name} {chart}", cmd_args)

        return create_tool_response(
            tool=self.config.name, command="upgrade", result=result
        )

    async def _rollback_release(self, args: Dict[str, Any]) -> ToolResponse:
        """Rollback a Helm release."""
        release_name = args["release"]
        revision = args["revision"]
        namespace = validate_namespace(args.get("namespace"))

        result = await self._execute_helm(
            f"rollback {release_name} {revision}",
            {"namespace": namespace, "wait": True},
        )

        return create_tool_response(
            tool=self.config.name, command="rollback", result=result
        )

    async def _uninstall_release(self, args: Dict[str, Any]) -> ToolResponse:
        """Uninstall a Helm release."""
        release_name = args["release"]
        namespace = validate_namespace(args.get("namespace"))

        result = await self._execute_helm(
            f"uninstall {release_name}", {"namespace": namespace}
        )

        return create_tool_response(
            tool=self.config.name, command="uninstall", result=result
        )

    async def _list_releases(self, args: Dict[str, Any]) -> ToolResponse:
        """List Helm releases."""
        namespace = args.get("namespace", "")  # Empty string means all namespaces

        cmd_args = {"all-namespaces": not namespace, "output": "json"}

        if namespace:
            cmd_args["namespace"] = namespace

        result = await self._execute_helm("list", cmd_args)

        return create_tool_response(
            tool=self.config.name, command="list", result=result
        )

    async def _get_status(self, args: Dict[str, Any]) -> ToolResponse:
        """Get Helm release status."""
        release_name = args["release"]
        namespace = validate_namespace(args.get("namespace"))

        result = await self._execute_helm(
            f"status {release_name}", {"namespace": namespace, "output": "json"}
        )

        return create_tool_response(
            tool=self.config.name, command="status", result=result
        )

    async def _manage_repo(self, args: Dict[str, Any]) -> ToolResponse:
        """Manage Helm repositories."""
        subcommand = args["subcommand"]  # add, remove, update, list

        if subcommand == "add":
            name = args["name"]
            url = args["url"]
            cmd = f"repo add {name} {url}"
        elif subcommand == "remove":
            name = args["name"]
            cmd = f"repo remove {name}"
        elif subcommand == "update":
            cmd = "repo update"
        elif subcommand == "list":
            cmd = "repo list"
        else:
            raise ValueError(f"Invalid repo subcommand: {subcommand}")

        result = await self._execute_helm(cmd, {})

        return create_tool_response(
            tool=self.config.name, command=f"repo {subcommand}", result=result
        )

    async def _get_release_info(self, args: Dict[str, Any]) -> ToolResponse:
        """Get information about a release."""
        release_name = args["release"]
        info_type = args["type"]  # values, manifest, hooks, notes
        namespace = validate_namespace(args.get("namespace"))

        result = await self._execute_helm(
            f"get {info_type} {release_name}", {"namespace": namespace}
        )

        return create_tool_response(
            tool=self.config.name, command=f"get {info_type}", result=result
        )

    async def _execute_helm(
        self, command: str, args: Dict[str, Any], input_data: Optional[Any] = None
    ) -> Any:
        """Execute a helm command through MCP."""
        executor = MCPExecutor()
        return await executor.execute(
            tool="helm", command=command, args=args, input_data=input_data
        )
