#!/bin/bash
set -e

echo "Starting Skyflo MCP Server..."
exec python main.py --host 0.0.0.0 --port 8888