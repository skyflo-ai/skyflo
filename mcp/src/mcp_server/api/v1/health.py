"""Health check endpoints for Kubernetes probes."""

from fastapi import APIRouter

router = APIRouter()

@router.get("")
async def health_check():
    """Basic health check endpoint for Kubernetes liveness and readiness probes."""
    return {"status": "healthy"} 