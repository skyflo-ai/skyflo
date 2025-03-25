"""FastAPI integration for Skyflo.ai MCP Server."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Skyflo.ai MCP Server API",
    description="API for Skyflo.ai MCP Server - Cloud Native operations through natural language",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from .v1 import router as v1_router

app.include_router(v1_router, prefix="/mcp/v1")
