"""Helm tools implementation."""

from typing import Annotated, Optional, Dict, Any
from autogen_core.tools import FunctionTool
import os
import yaml

from .._utils import create_typed_fn_tool, run_command
from ..utils.helpers import create_yaml_file


def _run_helm_command(command: str) -> str:
    """Run a helm command and return its output."""
    # Split the command and remove empty strings
    cmd_parts = [part for part in command.split(" ") if part]
    return run_command("helm", cmd_parts)


def _helm_list_releases(
    namespace: Annotated[Optional[str], "The namespace to list releases from"],
    all_namespaces: Annotated[
        Optional[bool], "Whether to list releases across all namespaces"
    ] = False,
) -> str:
    """List helm releases."""
    return _run_helm_command(
        f"list {f'-n {namespace}' if namespace else ''} {'-A' if all_namespaces else ''}"
    )


def _helm_repo_add(
    name: Annotated[str, "The name of the repository"],
    url: Annotated[str, "The URL of the repository"],
) -> str:
    """Add a helm repository."""
    return _run_helm_command(f"repo add {name} {url}")


def _helm_repo_update() -> str:
    """Update helm repositories."""
    return _run_helm_command("repo update")


def _helm_repo_remove(name: Annotated[str, "The name of the repository"]) -> str:
    """Remove a helm repository."""
    return _run_helm_command(f"repo remove {name}")


def _helm_install(
    name: Annotated[str, "The name of the release"],
    chart: Annotated[str, "The chart to install"],
    version: Annotated[str, "The version of the chart"],
) -> str:
    """Install a helm release."""
    return _run_helm_command(f"install {name} {chart} --version {version}")


def _helm_install_with_values(
    name: Annotated[str, "The name of the release"],
    chart: Annotated[str, "The chart to install"],
    version: Annotated[str, "The version of the chart"],
    values: Annotated[Dict[str, Any], "The values to use for installation"],
    namespace: Annotated[
        Optional[str], "The namespace to install the release in"
    ] = None,
) -> str:
    """Install a helm release with custom values."""
    try:
        # Create a temporary values file
        values_file = create_yaml_file(values, prefix=f"helm_{name}")

        # Build the command
        cmd = f"install {name} {chart} --version {version} --values {values_file}"
        if namespace:
            cmd += f" --namespace {namespace} --create-namespace"

        # Run the command
        result = _run_helm_command(cmd)

        # Cleanup
        try:
            os.unlink(values_file)
        except:
            pass  # Ignore cleanup errors

        return result
    except Exception as e:
        return f"Error installing chart: {str(e)}"


def _generate_helm_values(
    values: Annotated[Dict[str, Any], "The values to generate a YAML file for"],
    output_path: Annotated[
        Optional[str], "The path to write the values to (optional)"
    ] = None,
) -> str:
    """Generate a YAML values file for Helm.

    If output_path is not provided, a temporary file will be created and its path returned.
    """
    try:
        if output_path:
            # Use the specified path
            with open(output_path, "w") as f:
                yaml.dump(values, f, default_flow_style=False)
            return f"Values file created at: {output_path}"
        else:
            # Create a temporary file
            values_file = create_yaml_file(values)
            return values_file
    except Exception as e:
        return f"Error generating values file: {str(e)}"


# Create function tools
helm_list_releases = FunctionTool(
    _helm_list_releases,
    description="List helm releases.",
    name="helm_list_releases",
)

helm_repo_add = FunctionTool(
    _helm_repo_add,
    description="Add a helm repository.",
    name="helm_repo_add",
)

helm_repo_update = FunctionTool(
    _helm_repo_update,
    description="Update helm repositories.",
    name="helm_repo_update",
)

helm_repo_remove = FunctionTool(
    _helm_repo_remove,
    description="Remove a helm repository.",
    name="helm_repo_remove",
)

helm_install_with_values = FunctionTool(
    _helm_install_with_values,
    description="Install a Helm chart with custom values.",
    name="helm_install_with_values",
)

generate_helm_values = FunctionTool(
    _generate_helm_values,
    description="Generate a YAML values file for Helm.",
    name="generate_helm_values",
)

# Create typed tools
HelmListReleases, HelmListReleasesConfig = create_typed_fn_tool(
    helm_list_releases, "engine.tools.helm.HelmListReleases", "HelmListReleases"
)

HelmRepoAdd, HelmRepoAddConfig = create_typed_fn_tool(
    helm_repo_add, "engine.tools.helm.HelmRepoAdd", "HelmRepoAdd"
)

HelmRepoUpdate, HelmRepoUpdateConfig = create_typed_fn_tool(
    helm_repo_update, "engine.tools.helm.HelmRepoUpdate", "HelmRepoUpdate"
)

HelmRepoRemove, HelmRepoRemoveConfig = create_typed_fn_tool(
    helm_repo_remove, "engine.tools.helm.HelmRepoRemove", "HelmRepoRemove"
)

HelmInstallWithValues, HelmInstallWithValuesConfig = create_typed_fn_tool(
    helm_install_with_values,
    "engine.tools.helm.HelmInstallWithValues",
    "HelmInstallWithValues",
)

GenerateHelmValues, GenerateHelmValuesConfig = create_typed_fn_tool(
    generate_helm_values, "engine.tools.helm.GenerateHelmValues", "GenerateHelmValues"
)
