"""Tests for tools.argo module."""

import pytest
from tools.argo import (
    run_argo_command
)


class TestRunArgoCommand:
    """Test cases for run_argo_command function."""

    @pytest.mark.asyncio
    async def test_run_argo_command_basic(self, mocker):
        """Test basic argo command execution."""
        mock_run_command = mocker.patch('tools.argo.run_command')
        mock_run_command.return_value = {"output": "argo output", "error": False}

        result = await run_argo_command("list rollouts")

        mock_run_command.assert_called_once_with("kubectl", ["argo", "rollouts", "list", "rollouts"])
        assert result == {"output": "argo output", "error": False}

    @pytest.mark.asyncio
    async def test_run_argo_command_with_spaces(self, mocker):
        """Test argo command with multiple spaces."""
        mock_run_command = mocker.patch('tools.argo.run_command')
        mock_run_command.return_value = {"output": "clean output", "error": False}

        result = await run_argo_command("get rollout   my-rollout")

        mock_run_command.assert_called_once_with("kubectl", ["argo", "rollouts", "get", "rollout", "my-rollout"])
        assert result == {"output": "clean output", "error": False}
