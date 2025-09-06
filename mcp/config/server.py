from fastmcp import FastMCP

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
    dependencies=[
        "pydantic",
        "kubernetes",
        "helm",
        "argo",
    ],
)

from tools import kubectl
from tools import helm
from tools import argo
