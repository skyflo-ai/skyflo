"""ASGI entry point for Skyflo.ai MCP Server service."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from concurrent.futures import ThreadPoolExecutor

from mcp_server.config.settings import settings

from .tools.registry import registry, ToolCategory
from .tools.k8s._kubectl import (
    get_pod_logs,
    get_resources,
    describe_resource,
    create_manifest,
    apply_manifest,
    patch_resource,
    update_resource_container_images,
    rollout_restart_deployment,
    scale,
    delete_resource,
    wait_for_x_seconds,
    rollout_status,
    get_cluster_info,
    cordon_node,
    uncordon_node,
    drain_node,
    run_pod,
    port_forward,
)
from .tools.argo import (
    get_rollouts,
    promote_rollout,
    pause_rollout,
    set_rollout_image,
    rollout_restart,
)
from .tools.helm._helm import (
    helm_list_releases,
    helm_repo_add,
    helm_repo_update,
    helm_repo_remove,
    helm_install_with_values,
    generate_helm_values,
)
from .api import app as fastapi_app
from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("Skyflo.ai MCP Server")


def register_k8s_tools():
    """Register Kubernetes tools."""
    tools = [
        (get_pod_logs._func, get_pod_logs.name, get_pod_logs.description),
        (get_resources._func, get_resources.name, get_resources.description),
        (
            describe_resource._func,
            describe_resource.name,
            describe_resource.description,
        ),
        (
            create_manifest._func,
            create_manifest.name,
            create_manifest.description,
        ),
        (
            apply_manifest._func,
            apply_manifest.name,
            apply_manifest.description,
        ),
        (
            update_resource_container_images._func,
            update_resource_container_images.name,
            update_resource_container_images.description,
        ),
        (patch_resource._func, patch_resource.name, patch_resource.description),
        (
            rollout_restart_deployment._func,
            rollout_restart_deployment.name,
            rollout_restart_deployment.description,
        ),
        (scale._func, scale.name, scale.description),
        (delete_resource._func, delete_resource.name, delete_resource.description),
        (
            wait_for_x_seconds._func,
            wait_for_x_seconds.name,
            wait_for_x_seconds.description,
        ),
        (
            rollout_status._func,
            rollout_status.name,
            rollout_status.description,
        ),
        (
            get_cluster_info._func,
            get_cluster_info.name,
            get_cluster_info.description,
        ),
        (
            cordon_node._func,
            cordon_node.name,
            cordon_node.description,
        ),
        (
            uncordon_node._func,
            uncordon_node.name,
            uncordon_node.description,
        ),
        (
            drain_node._func,
            drain_node.name,
            drain_node.description,
        ),
        (
            run_pod._func,
            run_pod.name,
            run_pod.description,
        ),
        (
            port_forward._func,
            port_forward.name,
            port_forward.description,
        ),
    ]

    for func, name, description in tools:
        mcp.add_tool(func, name, description)
        registry.register_tool(name, description, ToolCategory.KUBERNETES, handler=func)


def register_argo_tools():
    """Register Argo tools."""
    tools = [
        (get_rollouts._func, get_rollouts.name, get_rollouts.description),
        (promote_rollout._func, promote_rollout.name, promote_rollout.description),
        (pause_rollout._func, pause_rollout.name, pause_rollout.description),
        (
            set_rollout_image._func,
            set_rollout_image.name,
            set_rollout_image.description,
        ),
        (rollout_restart._func, rollout_restart.name, rollout_restart.description),
    ]

    for func, name, description in tools:
        mcp.add_tool(func, name, description)
        registry.register_tool(name, description, ToolCategory.ARGO, handler=func)


def register_helm_tools():
    """Register Helm tools."""
    tools = [
        (
            helm_list_releases._func,
            helm_list_releases.name,
            helm_list_releases.description,
        ),
        (helm_repo_add._func, helm_repo_add.name, helm_repo_add.description),
        (helm_repo_update._func, helm_repo_update.name, helm_repo_update.description),
        (helm_repo_remove._func, helm_repo_remove.name, helm_repo_remove.description),
        (
            helm_install_with_values._func,
            helm_install_with_values.name,
            helm_install_with_values.description,
        ),
        (
            generate_helm_values._func,
            generate_helm_values.name,
            generate_helm_values.description,
        ),
    ]

    for func, name, description in tools:
        mcp.add_tool(func, name, description)
        registry.register_tool(name, description, ToolCategory.HELM, handler=func)


def register_all_tools():
    """Register all available tools."""
    # Clear existing registrations
    registry.clear()

    # Register all tools
    register_k8s_tools()
    register_argo_tools()
    register_helm_tools()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Starting Skyflo.ai MCP Server")
    register_all_tools()

    # Start MCP server in a separate thread
    executor = ThreadPoolExecutor(max_workers=1)
    executor.submit(mcp.run)

    yield

    # Shutdown
    logger.info("Shutting down Skyflo.ai MCP Server")
    executor.shutdown(wait=True)


def create_application() -> FastAPI:
    """Create the FastAPI application."""
    application = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    # Configure CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure as needed
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount the FastAPI app
    application.mount("", fastapi_app)

    return application


# Create and export the FastAPI application
app = create_application()
