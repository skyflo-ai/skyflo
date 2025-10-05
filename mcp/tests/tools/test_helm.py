"""Tests for tools.helm module."""

import pytest
from tools.helm import (
    run_helm_command
)


class TestRunHelmCommand:
    """Test cases for run_helm_command function."""

    @pytest.mark.asyncio
    async def test_run_helm_command_basic(self, mocker):
        """Test basic helm command execution."""
        mock_run_command = mocker.patch('tools.helm.run_command')
        mock_run_command.return_value = {"output": "helm output", "error": False}

        result = await run_helm_command("list")

        mock_run_command.assert_called_once_with("helm", ["list"])
        assert result == {"output": "helm output", "error": False}

    @pytest.mark.asyncio
    async def test_run_helm_command_with_spaces(self, mocker):
        """Test helm command with multiple spaces."""
        mock_run_command = mocker.patch('tools.helm.run_command')
        mock_run_command.return_value = {"output": "clean output", "error": False}

        result = await run_helm_command("install   my-release nginx")

        mock_run_command.assert_called_once_with("helm", ["install", "my-release", "nginx"])
        assert result == {"output": "clean output", "error": False}
