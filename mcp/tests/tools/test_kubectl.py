"""Simplified tests for tools.kubectl module focusing on core logic."""

from unittest.mock import AsyncMock, patch

import pytest

from tools.kubectl import (
    build_kubectl_top_args,
    k8s_exec,
    k8s_get,
    k8s_patch,
    k8s_run_pod,
    run_kubectl_command,
)


class TestRunKubectlCommand:
    """Test cases for run_kubectl_command function."""

    @pytest.mark.asyncio
    async def test_run_kubectl_command_basic(self):
        """Test basic kubectl command execution."""
        with patch("tools.kubectl.run_command", new_callable=AsyncMock) as mock_run_command:
            mock_run_command.return_value = {"output": "kubectl output", "error": False}

            result = await run_kubectl_command("get pods")

            mock_run_command.assert_called_once_with("kubectl", ["get", "pods"], stdin=None)
            assert result == {"output": "kubectl output", "error": False}

    @pytest.mark.asyncio
    async def test_run_kubectl_command_with_stdin(self):
        """Test kubectl command with stdin input."""
        with patch("tools.kubectl.run_command", new_callable=AsyncMock) as mock_run_command:
            mock_run_command.return_value = {"output": "applied", "error": False}

            result = await run_kubectl_command("apply -f -", stdin="apiVersion: v1")

            mock_run_command.assert_called_once_with(
                "kubectl", ["apply", "-f", "-"], stdin="apiVersion: v1"
            )
            assert result == {"output": "applied", "error": False}

    @pytest.mark.asyncio
    async def test_run_kubectl_command_empty_parts(self):
        """Test kubectl command with empty parts filtered out."""
        with patch("tools.kubectl.run_command", new_callable=AsyncMock) as mock_run_command:
            mock_run_command.return_value = {"output": "output", "error": False}

            result = await run_kubectl_command("get pods")

            mock_run_command.assert_called_once_with("kubectl", ["get", "pods"], stdin=None)
            assert result == {"output": "output", "error": False}

    @pytest.mark.asyncio
    async def test_run_kubectl_command_multiple_spaces(self):
        """Test kubectl command with multiple consecutive spaces."""
        with patch("tools.kubectl.run_command", new_callable=AsyncMock) as mock_run_command:
            mock_run_command.return_value = {"output": "output", "error": False}

            result = await run_kubectl_command("get pods -n default")

            mock_run_command.assert_called_once_with(
                "kubectl", ["get", "pods", "-n", "default"], stdin=None
            )
            assert result == {"output": "output", "error": False}

    @pytest.mark.asyncio
    async def test_run_kubectl_command_complex_command(self):
        """Test kubectl command with complex arguments."""
        with patch("tools.kubectl.run_command", new_callable=AsyncMock) as mock_run_command:
            mock_run_command.return_value = {"output": "output", "error": False}

            result = await run_kubectl_command("get pods -n kube-system --selector=app=nginx")

            mock_run_command.assert_called_once_with(
                "kubectl", ["get", "pods", "-n", "kube-system", "--selector=app=nginx"], stdin=None
            )
            assert result == {"output": "output", "error": False}

    @pytest.mark.asyncio
    async def test_run_kubectl_command_single_word(self):
        """Test kubectl command with single word."""
        with patch("tools.kubectl.run_command", new_callable=AsyncMock) as mock_run_command:
            mock_run_command.return_value = {"output": "cluster-info", "error": False}

            result = await run_kubectl_command("cluster-info")

            mock_run_command.assert_called_once_with("kubectl", ["cluster-info"], stdin=None)
            assert result == {"output": "cluster-info", "error": False}

    @pytest.mark.asyncio
    async def test_run_kubectl_command_error_propagation(self):
        """Test that errors from run_command are properly propagated."""
        with patch("tools.kubectl.run_command", new_callable=AsyncMock) as mock_run_command:
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
            sort_by="memory",
        )
        expected = [
            "top",
            "pods",
            "test-pod",
            "-n",
            "test-ns",
            "--containers",
            "--no-headers",
            "-l",
            "app=nginx",
            "--sort-by",
            "memory",
        ]
        assert args == expected


class TestK8sPatch:
    """Test cases for k8s_patch function with space handling."""

    @pytest.mark.asyncio
    async def test_k8s_patch_with_json_spaces(self):
        """Test that JSON patches with spaces are handled correctly."""
        with patch("tools.kubectl.run_command", new_callable=AsyncMock) as mock_run_command:
            mock_run_command.return_value = {"output": "patched", "error": False}

            patch_json = '{"spec": {"replicas": 3}}'
            await k8s_patch.fn(
                name="nginx",
                resource_type="deployment",
                patch=patch_json,
                namespace="default",
                patch_type="strategic",
            )

            mock_run_command.assert_called_once_with(
                "kubectl",
                [
                    "patch",
                    "deployment",
                    "nginx",
                    "-n",
                    "default",
                    "--patch",
                    '{"spec": {"replicas": 3}}',
                    "--type=strategic",
                ],
            )

    @pytest.mark.asyncio
    async def test_k8s_patch_without_namespace(self):
        """Test patch without namespace."""
        with patch("tools.kubectl.run_command", new_callable=AsyncMock) as mock_run_command:
            mock_run_command.return_value = {"output": "patched", "error": False}

            await k8s_patch.fn(
                name="nginx",
                resource_type="deployment",
                patch='{"spec": {"replicas": 5}}',
                namespace=None,
                patch_type="merge",
            )

            mock_run_command.assert_called_once_with(
                "kubectl",
                [
                    "patch",
                    "deployment",
                    "nginx",
                    "--patch",
                    '{"spec": {"replicas": 5}}',
                    "--type=merge",
                ],
            )


class TestK8sExec:
    """Test cases for k8s_exec function with space handling."""

    @pytest.mark.asyncio
    async def test_k8s_exec_with_spaces_in_command(self):
        """Test that commands with spaces are handled correctly."""
        with patch("tools.kubectl.run_command", new_callable=AsyncMock) as mock_run_command:
            mock_run_command.return_value = {"output": "output", "error": False}

            await k8s_exec.fn(pod_name="nginx-pod", command="ls -la /tmp", namespace="default")

            mock_run_command.assert_called_once_with(
                "kubectl", ["exec", "nginx-pod", "-n", "default", "--", "ls", "-la", "/tmp"]
            )

    @pytest.mark.asyncio
    async def test_k8s_exec_with_container(self):
        """Test exec with container specified."""
        with patch("tools.kubectl.run_command", new_callable=AsyncMock) as mock_run_command:
            mock_run_command.return_value = {"output": "output", "error": False}

            await k8s_exec.fn(
                pod_name="nginx-pod",
                command="cat /etc/nginx/nginx.conf",
                namespace="web",
                container="nginx",
            )

            mock_run_command.assert_called_once_with(
                "kubectl",
                [
                    "exec",
                    "nginx-pod",
                    "-n",
                    "web",
                    "-c",
                    "nginx",
                    "--",
                    "cat",
                    "/etc/nginx/nginx.conf",
                ],
            )


class TestK8sRunPod:
    """Test cases for k8s_run_pod function with space handling."""

    @pytest.mark.asyncio
    async def test_k8s_run_pod_with_command_spaces(self):
        """Test that commands with spaces are handled correctly."""
        with patch("tools.kubectl.run_command", new_callable=AsyncMock) as mock_run_command:
            mock_run_command.return_value = {"output": "output", "error": False}

            await k8s_run_pod.fn(
                name="debug-pod", image="busybox", namespace="default", command="sleep 3600"
            )

            mock_run_command.assert_called_once_with(
                "kubectl",
                [
                    "run",
                    "debug-pod",
                    "--image=busybox",
                    "-n",
                    "default",
                    "--command",
                    "--",
                    "sleep",
                    "3600",
                ],
            )

    @pytest.mark.asyncio
    async def test_k8s_run_pod_without_command(self):
        """Test run pod without command."""
        with patch("tools.kubectl.run_command", new_callable=AsyncMock) as mock_run_command:
            mock_run_command.return_value = {"output": "output", "error": False}

            await k8s_run_pod.fn(name="nginx-pod", image="nginx:latest", namespace="web")

            mock_run_command.assert_called_once_with(
                "kubectl", ["run", "nginx-pod", "--image=nginx:latest", "-n", "web"]
            )


class TestK8sGet:
    """Test cases for k8s_get function with space handling."""

    @pytest.mark.asyncio
    async def test_k8s_get_with_label_selector_spaces(self):
        """Test that label selectors with spaces are handled correctly."""
        with patch("tools.kubectl.run_command", new_callable=AsyncMock) as mock_run_command:
            mock_run_command.return_value = {"output": "output", "error": False}

            await k8s_get.fn(
                resource_type="pods", label_selector="app in (nginx, apache)", namespace="default"
            )

            mock_run_command.assert_called_once_with(
                "kubectl", ["get", "pods", "-n", "default", "-l", "app in (nginx, apache)"]
            )

    @pytest.mark.asyncio
    async def test_k8s_get_with_all_options(self):
        """Test get with multiple options."""
        with patch("tools.kubectl.run_command", new_callable=AsyncMock) as mock_run_command:
            mock_run_command.return_value = {"output": "output", "error": False}

            await k8s_get.fn(
                resource_type="deployments", name="nginx", namespace="web", output="yaml"
            )

            mock_run_command.assert_called_once_with(
                "kubectl", ["get", "deployments", "nginx", "-n", "web", "-o", "yaml"]
            )

    @pytest.mark.asyncio
    async def test_k8s_get_all_namespaces(self):
        """Test get with all namespaces."""
        with patch("tools.kubectl.run_command", new_callable=AsyncMock) as mock_run_command:
            mock_run_command.return_value = {"output": "output", "error": False}

            await k8s_get.fn(resource_type="pods", all_namespaces=True)

            mock_run_command.assert_called_once_with("kubectl", ["get", "pods", "-A"])
