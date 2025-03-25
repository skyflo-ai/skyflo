#!/bin/bash
set -e

# Start the Engine service with Uvicorn
echo "Starting MCP service..."
exec uvicorn api.asgi:app --host 0.0.0.0 --port 8081 --workers ${MCP_SERVER_WORKERS:-2} 