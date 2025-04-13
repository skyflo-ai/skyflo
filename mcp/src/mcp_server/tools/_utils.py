"""Common utilities for tool creation."""

from typing import Any, Optional
import subprocess
import asyncio
import os
import yaml
import tempfile
from autogen_core import CancellationToken, Component
from autogen_core.tools import BaseTool, FunctionTool
from pydantic import BaseModel
from ..utils.retry import with_retry


def create_typed_fn_tool(
    fn_tool: FunctionTool, override_provider: str, class_name: str
):
    """Creates a concrete typed fn tool class from a function tool."""

    class ToolConfig(BaseModel):
        pass

    class Tool(BaseTool, Component[ToolConfig]):
        component_provider_override = override_provider
        component_type = "tool"
        component_config_schema = ToolConfig
        component_description = fn_tool.description

        def __init__(self):
            self.fn_tool = fn_tool
            super().__init__(
                name=fn_tool.name,
                description=fn_tool.description,
                args_type=fn_tool.args_type(),
                return_type=fn_tool.return_type(),
            )

        async def run(
            self, args: ToolConfig, cancellation_token: CancellationToken
        ) -> Any:
            return await self.fn_tool.run(args, cancellation_token)

        def _to_config(self) -> ToolConfig:
            return ToolConfig()

        @classmethod
        def _from_config(cls, config: ToolConfig):
            return cls()

    # Set the class name dynamically
    Tool.__name__ = class_name
    ToolConfig.__name__ = class_name + "Config"
    return (Tool, ToolConfig)


@with_retry
async def run_command(cmd: str, args: list[str]) -> str:
    """Run a command and return its output with retry logic."""
    try:
        proc = await asyncio.create_subprocess_exec(
            cmd,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            error_msg = stderr.decode().strip()
            if "i/o timeout" in error_msg.lower():
                raise asyncio.TimeoutError(error_msg)
            return f"Error executing command {cmd} with args {args}: {error_msg}"

        return stdout.decode().strip()
    except asyncio.TimeoutError:
        raise  # Let the retry decorator handle timeouts
    except Exception as e:
        return f"Error executing command {cmd} with args {args}: {str(e)}"


class ManifestError(Exception):
    """Base exception for manifest operations."""

    pass


class InvalidManifestError(ManifestError):
    """Raised when manifest content is invalid."""

    pass


class ManifestFileError(ManifestError):
    """Raised when there's an error handling manifest files."""

    pass


@with_retry
async def exec_create_manifest(name: str, content: str) -> str:
    """Create a Kubernetes manifest file with retry logic.

    Args:
        content: The YAML manifest content
        name: The name of the manifest file

    Returns:
        str: Path to the created manifest file

    Raises:
        InvalidManifestError: If YAML content is invalid
        ManifestFileError: If file operations fail
    """
    try:
        # Ensure the manifests directory exists in the system temp directory
        manifests_dir = os.path.join(tempfile.gettempdir(), "skyflo", "manifests")
        os.makedirs(manifests_dir, exist_ok=True)

        # Ensure manifest name ends with .yaml or .yml
        if not name.endswith((".yaml", ".yml")):
            name += ".yaml"

        # Create full file path
        file_path = os.path.join(manifests_dir, name)

        # Validate YAML content
        try:
            yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise InvalidManifestError(f"Invalid YAML content: {str(e)}")

        # Write manifest to file
        try:
            with open(file_path, "w") as f:
                f.write(content)
        except IOError as e:
            raise ManifestFileError(f"Failed to write manifest file: {str(e)}")

        return file_path

    except (InvalidManifestError, ManifestFileError):
        raise
    except Exception as e:
        raise ManifestFileError(f"Unexpected error creating manifest: {str(e)}")
