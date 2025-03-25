"""Argo Rollouts tools implementation."""

from typing import Annotated, Optional
from autogen_core.tools import FunctionTool

from .._utils import create_typed_fn_tool, run_command


async def _run_argo_command(command: str) -> str:
    """Run an argo rollouts command and return its output."""
    # Split the command and remove empty strings
    cmd_parts = [part for part in command.split(" ") if part]
    return await run_command("kubectl", ["argo", "rollouts"] + cmd_parts)


async def _get_rollouts(
    namespace: Annotated[Optional[str], "The namespace of the rollout"],
) -> str:
    """Get all Argo rollouts using kubectl get command since 'get rollouts' is not supported."""
    # Use kubectl get directly since 'argo rollouts get rollouts' is not supported
    return await run_command(
        "kubectl",
        ["get", "rollouts.argoproj.io", "-o", "wide"]
        + (["-n", namespace] if namespace else []),
    )


async def _promote_rollout(
    name: Annotated[str, "The name of the rollout to promote"],
    namespace: Annotated[Optional[str], "The namespace of the rollout"],
    full: Annotated[
        Optional[bool],
        "Whether to do a full promotion (skip analysis, pauses, and steps)",
    ] = False,
) -> str:
    """Promote an Argo rollout."""
    return await _run_argo_command(
        f"promote {name} {f'-n {namespace}' if namespace else ''} {'--full' if full else ''}"
    )


async def _pause_rollout(
    name: Annotated[str, "The name of the rollout to pause"],
    namespace: Annotated[Optional[str], "The namespace of the rollout"],
) -> str:
    """Pause an Argo rollout."""
    return await _run_argo_command(
        f"pause {name} {f'-n {namespace}' if namespace else ''}"
    )


async def _set_rollout_image(
    name: Annotated[str, "The name of the rollout"],
    container_image: Annotated[
        str, "The container image to set (format: container=image)"
    ],
    namespace: Annotated[Optional[str], "The namespace of the rollout"],
) -> str:
    """Set the image for a container in an Argo rollout."""
    return await _run_argo_command(
        f"set image {name} {container_image} {f'-n {namespace}' if namespace else ''}"
    )


async def _rollout_restart(
    name: Annotated[str, "The name of the rollout"],
    namespace: Annotated[Optional[str], "The namespace of the rollout"],
) -> str:
    """Restart an Argo rollout."""
    return await _run_argo_command(
        f"restart {name} {f'-n {namespace}' if namespace else ''}"
    )


# Create function tools
get_rollouts = FunctionTool(
    _get_rollouts,
    description="List all Argo rollouts in a namespace using kubectl get command.",
    name="get_rollouts",
)

promote_rollout = FunctionTool(
    _promote_rollout,
    description="Promote an Argo rollout.",
    name="promote_rollout",
)

pause_rollout = FunctionTool(
    _pause_rollout,
    description="Pause an Argo rollout.",
    name="pause_rollout",
)

set_rollout_image = FunctionTool(
    _set_rollout_image,
    description="Set the image for a container in an Argo rollout.",
    name="set_rollout_image",
)

rollout_restart = FunctionTool(
    _rollout_restart,
    description="Restart an Argo rollout.",
    name="rollout_restart",
)

# Create typed tools
GetRollouts, GetRolloutsConfig = create_typed_fn_tool(
    get_rollouts, "engine.tools.argo.GetRollouts", "GetRollouts"
)

PromoteRollout, PromoteRolloutConfig = create_typed_fn_tool(
    promote_rollout, "engine.tools.argo.PromoteRollout", "PromoteRollout"
)

PauseRollout, PauseRolloutConfig = create_typed_fn_tool(
    pause_rollout, "engine.tools.argo.PauseRollout", "PauseRollout"
)

SetRolloutImage, SetRolloutImageConfig = create_typed_fn_tool(
    set_rollout_image, "engine.tools.argo.SetRolloutImage", "SetRolloutImage"
)

RolloutRestart, RolloutRestartConfig = create_typed_fn_tool(
    rollout_restart, "engine.tools.argo.RolloutRestart", "RolloutRestart"
)
