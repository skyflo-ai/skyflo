# MCP Server for Skyflo.ai

This is the MCP server for Skyflo.ai. It unifies Kubernetes (kubectl, Argo Rollouts, Helm) and CI/CD systems (starting with Jenkins) behind a FastMCP server, enabling natural-language execution by the [Engine](../engine) with integration-aware tool discovery, and secure credential resolution over HTTP or SSE.

## Architecture

The MCP Server is built using FastMCP:

### FastMCP Server

The FastMCP server serves as the core tool execution engine:

- Single entrypoint through `server.py`
- Registers standardized tool definitions for kubectl, argo rollouts, helm, and jenkins
- Implements safety mechanisms and validation checks
- Handles both synchronous and asynchronous operations
- Supports comprehensive tool documentation and metadata
- Built-in HTTP and SSE transport support
- Automatic tool discovery and registration

## Features

### Tool Categories

1. `kubectl` - Kubernetes tools: [/tools/kubectl.py](tools/kubectl.py)
2. `argo` - Argo Rollouts tools: [/tools/argo.py](tools/argo.py)
3. `helm` - Helm tools: [/tools/helm.py](tools/helm.py)
4. `jenkins` - Jenkins tools: [/tools/jenkins.py](tools/jenkins.py)

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
# Navigate to the mcp directory
cd mcp

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Unix or MacOS
.venv\Scripts\activate     # On Windows

# Install the package
uv pip install -e .
```

3. Start the server:

```console
# Start with HTTP transport (default)
uv run python main.py --host 0.0.0.0 --port 8888

# Or start with SSE transport
uv run python main.py --sse --host 0.0.0.0 --port 8888
```

The server provides MCP (Model Communication Protocol) interface for AI agents to interact with cloud-native tools.

## Testing

### Running Tests

The MCP server includes comprehensive test coverage for all tool implementations. Tests are organized in a structured directory layout that mirrors the source code:

```
tests/
├── tools/                   # Tests for tool implementations
│   ├── test_argo.py        # Argo Rollouts tests
│   ├── test_helm.py        # Helm tests
│   ├── test_jenkins.py     # Jenkins tests
│   └── test_kubectl.py     # Kubernetes tests
└── utils/                  # Tests for utility functions
    └── test_commands.py    # Command execution tests
```

#### Quick Start

**Using the test runner script**

```bash
# Navigate to mcp directory
cd mcp

# Run all tests with default coverage (30%)
./run_tests.sh

# Run tests with custom coverage threshold
./run_tests.sh --coverage 80
```

## Development

### Component Structure

```
mcp/
├── tools/                   # Tool implementations
│   ├── __init__.py          # Package initialization
│   ├── kubectl.py           # Kubernetes tools
│   ├── argo.py              # Argo Rollouts tools
│   ├── helm.py              # Helm tools
│   └── jenkins.py           # Jenkins tools
├── config/server.py         # FastMCP server entrypoint
├── __about__.py             # Version information
├── pyproject.toml           # Project dependencies
└── README.md                # Documentation
```

### Best Practices

- **Tool Implementation**

  - Use clear documentation and type hints with Pydantic Field descriptions
  - Implement proper error handling and validation
  - Follow async/await patterns for command execution
  - Register tools using the `register_tools(mcp)` pattern

- **Server Development**
  - Use FastMCP decorators for tool registration
  - Implement proper command execution with error handling
  - Provide clear tool descriptions and parameter documentation

## Community and Support

- [Website](https://skyflo.ai)
- [Discord Community](https://discord.gg/kCFNavMund)
- [Twitter/X Updates](https://x.com/skyflo_ai)
- [GitHub Discussions](https://github.com/skyflo-ai/skyflo/discussions)
