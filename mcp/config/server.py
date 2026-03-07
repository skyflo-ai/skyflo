import shutil

from fastmcp import FastMCP
from starlette.responses import JSONResponse

mcp = FastMCP(
    "Skyflo.ai MCP Server",
    instructions="""
    # Kubernetes DevOps MCP

    This MCP allows you to:
    1. Manage Kubernetes clusters, resources, and deployments using kubectl operations
    2. Install and manage applications with Helm charts and repositories
    3. Execute progressive deployments with Argo Rollouts (blue/green, canary strategies)
    4. Troubleshoot and diagnose cluster issues with comprehensive validation
    """,
)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    return JSONResponse({"status": "ok"})


@mcp.custom_route("/health/startup", methods=["GET"])
async def health_startup(request):
    return JSONResponse({"status": "ok"})


@mcp.custom_route("/health/ready", methods=["GET"])
async def health_ready(request):
    required_tools = ["kubectl", "helm", "kubectl-argo-rollouts"]
    missing_tools = [tool for tool in required_tools if shutil.which(tool) is None]
    if missing_tools:
        return JSONResponse({"status": "error", "missing_tools": missing_tools}, status_code=503)
    return JSONResponse({"status": "ready"})


# Import tool modules to register them with the MCP server
# The @mcp.tool() decorators execute at import time
import tools.argo  # noqa: E402, F401
import tools.helm  # noqa: E402, F401
import tools.jenkins  # noqa: E402, F401
import tools.kubectl  # noqa: E402, F401
