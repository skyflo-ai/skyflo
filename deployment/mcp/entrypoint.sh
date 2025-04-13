#!/bin/bash
set -e

# Start the Engine service with Uvicorn
echo "Starting MCP service..."
exec uvicorn mcp_server.asgi:app --host 0.0.0.0 --port 8081