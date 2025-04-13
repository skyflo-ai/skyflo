# MCP Server for Skyflo.ai

[![Python](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org)

## Overview

This is the MCP server for Skyflo.ai. It is a specialized infrastructure tools MCP server that enables natural language interactions with Kubernetes clusters through standardized interfaces for kubectl, Argo Rollouts, and Helm operations. It powers the Engine service by exposing a well-defined set of tools through a dual-server architecture.

## Architecture

The MCP Server implements a dual-server architecture built using FastAPI and FastMCP:

### MCP (Model Communicator Protocol) Server

The MCP server serves as the core tool execution engine:

- Registers standardized tool definitions for kubectl, argo rollouts, and helm
- Implements safety mechanisms and validation checks
- Runs on a dedicated thread for efficient tool execution
- Handles both synchronous and asynchronous operations
- Supports comprehensive tool documentation and metadata
- Provides structured categorization and discovery mechanisms

### FastAPI Server

The FastAPI server provides a RESTful API interface:

- Built on Uvicorn ASGI server for high performance
- Comprehensive Tools API at `/engine/v1/tools`
- Concurrent operation with the MCP server
- Structured error handling and response formatting
- Support for streaming responses and async execution

## Features

### Tool Categories

1. `k8s` - Kubernetes tools: [/src/tools/k8s/_kubectl.py](src/tools/k8s/_kubectl.py)
2. `argo` - Argo Rollouts tools: [/src/tools/argo/_argo_rollouts.py](src/tools/argo/_argo_rollouts.py)
3. `helm` - Helm tools: [/src/tools/helm/_helm.py](src/tools/helm/_helm.py)

## Installation

### Prerequisites

- Python 3.11+
- Kubernetes cluster (with kubectl configured)
- Argo Rollouts (optional)
- Helm (optional)

### Setup

1. Install `uv` package manager:

```console
# Install uv for macOS or Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or install with pip
pip install uv
```

2. Prepare your environment:

```console
# Navigate to the engine directory
cd engine

# Copy the .env.example file to .env
cp .env.example .env

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Unix or MacOS
.venv\Scripts\activate     # On Windows

# Install the engine package
uv pip install -e .
```

3. Start the server:

```console
source .venv/bin/activate && uvicorn mcp_server.asgi:app --host 0.0.0.0 --port 8081 --reload
```

The server exposes these endpoints:
- Tools API: `http://localhost:8081/engine/v1/tools`


## Development

### Component Structure

```
mcp/
├── src/
│   └── mcp_server/
│       ├── tools/           # Tool implementations
│       │   ├── k8s/         # Kubernetes tools
│       │   ├── argo/        # Argo tools
│       │   ├── helm/        # Helm tools
│       │   └── utils/       # Shared tool utilities
│       ├── api/             # FastAPI application
│       ├── config/          # Configuration management
│       └── asgi.py          # Application entry point
└── pyproject.toml           # Project dependencies
```

### Best Practices

- **Tool Implementation**
  - Use clear documentation and type hints
  - Implement proper error handling
  - Follow comprehensive testing standards

- **API Development**
  - Follow RESTful principles
  - Provide clear response formats and status codes
  - Implement proper request validation

- **Security**
  - Validate all user inputs
  - Follow authentication best practices
  - Implement audit logging for operations

- **Performance**
  - Use async operations where appropriate
  - Implement proper caching
  - Ensure proper resource cleanup

## Community and Support

- [Website](https://skyflo.ai)
- [Discord Community](https://discord.gg/kCFNavMund)
- [Twitter/X Updates](https://x.com/skyflo_ai)
- [GitHub Discussions](https://github.com/skyflo-ai/skyflo/discussions)
