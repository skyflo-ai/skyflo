"""Simplified tests for tools.kubectl module focusing on core logic."""

import pytest
import tools.kubectl
from tools.kubectl import (
    run_kubectl_command,
    build_kubectl_top_args
)


class TestRunKubectlCommand:
    """Test cases for run_kubectl_command function."""

    @pytest.mark.asyncio
    async def test_run_kubectl_command_basic(self, mocker):
        """Test basic kubectl command execution."""
        mock_run_command = mocker.patch('tools.kubectl.run_command')
        mock_run_command.return_value = {"output": "kubectl output", "error": False}

        result = await run_kubectl_command("get pods")

        mock_run_command.assert_called_once_with("kubectl", ["get", "pods"], stdin=None)
        assert result == {"output": "kubectl output", "error": False}

    @pytest.mark.asyncio
    async def test_run_kubectl_command_with_stdin(self, mocker):
        """Test kubectl command with stdin input."""
        mock_run_command = mocker.patch('tools.kubectl.run_command')
        mock_run_command.return_value = {"output": "applied", "error": False}

        result = await run_kubectl_command("apply -f -", stdin="apiVersion: v1")

        mock_run_command.assert_called_once_with("kubectl", ["apply", "-f", "-"], stdin="apiVersion: v1")
        assert result == {"output": "applied", "error": False}

    @pytest.mark.asyncio
    async def test_run_kubectl_command_empty_parts(self, mocker):
        """Test kubectl command with empty parts filtered out."""
        mock_run_command = mocker.patch('tools.kubectl.run_command')
        mock_run_command.return_value = {"output": "output", "error": False}

        result = await run_kubectl_command("get pods")

        mock_run_command.assert_called_once_with("kubectl", ["get", "pods"], stdin=None)
        assert result == {"output": "output", "error": False}

    @pytest.mark.asyncio
    async def test_run_kubectl_command_multiple_spaces(self, mocker):
        """Test kubectl command with multiple consecutive spaces."""
        mock_run_command = mocker.patch('tools.kubectl.run_command')
        mock_run_command.return_value = {"output": "output", "error": False}

        result = await run_kubectl_command("get pods -n default")

        mock_run_command.assert_called_once_with("kubectl", ["get", "pods", "-n", "default"], stdin=None)
        assert result == {"output": "output", "error": False}

    @pytest.mark.asyncio
    async def test_run_kubectl_command_no_split_characters(self, mocker):
        """Test kubectl command with no spaces (treated as single token)."""
        mock_run_command = mocker.patch('tools.kubectl.run_command')
        mock_run_command.return_value = {"output": "output", "error": False}

        result = await run_kubectl_command("get pods -n default")

        # Command without spaces is treated as a single token
        mock_run_command.assert_called_once_with("kubectl", ["get", "pods", "-n", "default"], stdin=None)
        assert result == {"output": "output", "error": False}

    @pytest.mark.asyncio
    async def test_run_kubectl_command_complex_command(self, mocker):
        """Test kubectl command with complex arguments."""
        mock_run_command = mocker.patch('tools.kubectl.run_command')
        mock_run_command.return_value = {"output": "output", "error": False}

        result = await run_kubectl_command("get pods -n kube-system --selector=app=nginx")

        mock_run_command.assert_called_once_with("kubectl", ["get", "pods", "-n", "kube-system", "--selector=app=nginx"], stdin=None)
        assert result == {"output": "output", "error": False}

    @pytest.mark.asyncio
    async def test_run_kubectl_command_single_word(self, mocker):
        """Test kubectl command with single word."""
        mock_run_command = mocker.patch('tools.kubectl.run_command')
        mock_run_command.return_value = {"output": "cluster-info", "error": False}

        result = await run_kubectl_command("cluster-info")

        mock_run_command.assert_called_once_with("kubectl", ["cluster-info"], stdin=None)
        assert result == {"output": "cluster-info", "error": False}

    @pytest.mark.asyncio
    async def test_run_kubectl_command_error_propagation(self, mocker):
        """Test that errors from run_command are properly propagated."""
        mock_run_command = mocker.patch('tools.kubectl.run_command')
        mock_run_command.return_value = {"output": "error message", "error": True}

        result = await run_kubectl_command("get pods")

        assert result == {"output": "error message", "error": True}
        mock_run_command.assert_called_once_with("kubectl", ["get", "pods"], stdin=None)


class TestBuildKubectlTopArgs:
    """Test cases for build_kubectl_top_args function."""

    def test_build_kubectl_top_args_basic(self):
        """Test basic top args building."""
        args = build_kubectl_top_args("pods")
        assert args == ["top", "pods"]

    def test_build_kubectl_top_args_with_name(self):
        """Test top args building with name."""
        args = build_kubectl_top_args("pods", name="test-pod")
        assert args == ["top", "pods", "test-pod"]

    def test_build_kubectl_top_args_with_namespace(self):
        """Test top args building with namespace."""
        args = build_kubectl_top_args("pods", namespace="test-ns")
        assert args == ["top", "pods", "-n", "test-ns"]

    def test_build_kubectl_top_args_all_namespaces(self):
        """Test top args building with all namespaces."""
        args = build_kubectl_top_args("pods", all_namespaces=True)
        assert args == ["top", "pods", "-A"]

    def test_build_kubectl_top_args_with_containers(self):
        """Test top args building with containers."""
        args = build_kubectl_top_args("pods", containers=True)
        assert args == ["top", "pods", "--containers"]

    def test_build_kubectl_top_args_with_no_headers(self):
        """Test top args building with no headers."""
        args = build_kubectl_top_args("pods", no_headers=True)
        assert args == ["top", "pods", "--no-headers"]

    def test_build_kubectl_top_args_with_label_selector(self):
        """Test top args building with label selector."""
        args = build_kubectl_top_args("pods", label_selector="app=nginx")
        assert args == ["top", "pods", "-l", "app=nginx"]

    def test_build_kubectl_top_args_with_sort_by(self):
        """Test top args building with sort by."""
        args = build_kubectl_top_args("pods", sort_by="cpu")
        assert args == ["top", "pods", "--sort-by", "cpu"]

    def test_build_kubectl_top_args_invalid_sort_by(self):
        """Test top args building with invalid sort by."""
        with pytest.raises(ValueError, match="sort_by must be 'cpu' or 'memory'"):
            build_kubectl_top_args("pods", sort_by="invalid")

    def test_build_kubectl_top_args_all_options(self):
        """Test top args building with all options."""
        args = build_kubectl_top_args(
            "pods",
            name="test-pod",
            namespace="test-ns",
            containers=True,
            no_headers=True,
            label_selector="app=nginx",
            sort_by="memory"
        )
        expected = [
            "top", "pods", "test-pod", "-n", "test-ns",
            "--containers", "--no-headers", "-l", "app=nginx",
            "--sort-by", "memory"
        ]
        assert args == expected
