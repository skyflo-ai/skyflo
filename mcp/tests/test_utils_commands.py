"""Tests for utils.commands module."""

import pytest
from utils.commands import run_command


class TestRunCommand:
    """Test cases for run_command function."""

    @pytest.mark.asyncio
    async def test_run_command_success(self, mocker):
        """Test successful command execution."""
        mock_subprocess = mocker.patch('asyncio.create_subprocess_exec')
        mock_proc = mocker.AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = mocker.AsyncMock(return_value=(b"success output", b""))
        mock_subprocess.return_value = mock_proc

        result = await run_command("test_cmd", ["arg1", "arg2"])

        assert result["output"] == "success output"
        assert result["error"] is False
        mock_subprocess.assert_called_once_with(
            "test_cmd", "arg1", "arg2",
            stdout=-1,
            stderr=-1,
            stdin=None
        )

    @pytest.mark.asyncio
    async def test_run_command_with_stdin(self, mocker):
        """Test command execution with stdin input."""
        mock_subprocess = mocker.patch('asyncio.create_subprocess_exec')
        mock_proc = mocker.AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = mocker.AsyncMock(return_value=(b"output with stdin", b""))
        mock_subprocess.return_value = mock_proc

        result = await run_command("test_cmd", ["arg1"], stdin="test input")

        assert result["output"] == "output with stdin"
        assert result["error"] is False
        mock_proc.communicate.assert_called_once_with(input=b"test input")

    @pytest.mark.asyncio
    async def test_run_command_error_return_code(self, mocker):
        """Test command execution with error return code."""
        mock_subprocess = mocker.patch('asyncio.create_subprocess_exec')
        mock_proc = mocker.AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate = mocker.AsyncMock(return_value=(b"", b"error message"))
        mock_subprocess.return_value = mock_proc

        result = await run_command("test_cmd", ["arg1"])

        assert "Error executing command" in result["output"]
        assert result["error"] is True

    @pytest.mark.asyncio
    async def test_run_command_stderr_output(self, mocker):
        """Test command execution with stderr output but success return code."""
        mock_subprocess = mocker.patch('asyncio.create_subprocess_exec')
        mock_proc = mocker.AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = mocker.AsyncMock(return_value=(b"", b"warning message"))
        mock_subprocess.return_value = mock_proc

        result = await run_command("test_cmd", ["arg1"])

        assert result["output"] == "warning message"
        assert result["error"] is True

    @pytest.mark.asyncio
    async def test_run_command_no_output(self, mocker):
        """Test command execution with no output."""
        mock_subprocess = mocker.patch('asyncio.create_subprocess_exec')
        mock_proc = mocker.AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = mocker.AsyncMock(return_value=(b"", b""))
        mock_subprocess.return_value = mock_proc

        result = await run_command("test_cmd", ["arg1"])

        assert "successfully" in result["output"]
        assert result["error"] is False

    @pytest.mark.asyncio
    async def test_run_command_exception(self, mocker):
        """Test command execution with exception."""
        mock_subprocess = mocker.patch('asyncio.create_subprocess_exec')
        mock_subprocess.side_effect = Exception("Process creation failed")

        result = await run_command("test_cmd", ["arg1"])

        assert "Error executing command" in result["output"]
        assert "Process creation failed" in result["output"]
        assert result["error"] is True
